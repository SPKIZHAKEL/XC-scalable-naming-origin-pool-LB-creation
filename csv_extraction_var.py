import csv
import requests
import os
from dotenv import load_dotenv
from tf_vars_actual_write import write_tfvars_file
from cleaning_csv import read_csv_first_9_columns_filtered

load_dotenv()

# loading environment var
api_key = os.getenv('TF_VAR_api_token')

import csv
import json
import requests


# CSV Processing 

def to_hcl_map(d, indent=0):
    #Converting Python dict into Terraform HCL map syntax.
    spaces = " " * indent
    inner_spaces = " " * (indent + 2)

    lines = ["{"]

    for key, value in d.items():
        if isinstance(value, dict):
            lines.append(f'{inner_spaces}{key} = {to_hcl_map(value, indent + 2)}')
        elif isinstance(value, list):
            list_str = json.dumps(value)
            lines.append(f'{inner_spaces}{key} = {list_str}')
        else:
            if isinstance(value, str):
                lines.append(f'{inner_spaces}{key} = "{value}"')
            else:
                lines.append(f'{inner_spaces}{key} = {value}')

    lines.append(f"{spaces}}}")
    return "\n".join(lines)

def batch_list(items, batch_size=10):
    """Yield successive batches of given size."""
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]

def classify_origin(origin):
    """Return private_ip or private_name depending on whether origin contains letters."""
    cleaned = origin.replace('.', '')
    if any(c.isalpha() for c in cleaned):
        return "private_name"
    return "private_ip"

def make_origin_pool_name(hostname):
    """Create <part1>-<part2>-origin from hostname."""
    parts = hostname.split(".")
    if len(parts) < 2:
        return None
    return f"{parts[0]}-{parts[1]}-origin"


# CSV Processing

def process_csv(rows):
    
    #Accepts a list of dictionaries (already read from CSV).
    #Produces batches, origin classification, cert names, origin pool names, and pool dict.
    
    uat_rows = []
    prod_rows = []
    origin_classification = []
    certificate_name = []
    origin_pool_name = []
    batches={}

    for row in rows:
        business_unit = row.get("SUBDIVISION", "").strip()
        env = row.get("PROD/UAT", "").strip().lower()
        hostname = row.get("HOSTNAME", "").strip()
        origin = row.get("ORIGIN IP / FQDN", "").strip()

        if env == "uat":
            uat_rows.append(row)
        elif env == "prod":
            prod_rows.append(row)

        origin_classification.append([origin, classify_origin(origin)])
        certificate_name.append(hostname.replace(".", "-"))

        opn = make_origin_pool_name(hostname)
        if opn:
            origin_pool_name.append(opn)

  

    # UAT batches
    for idx, batch in enumerate(batch_list(uat_rows, 10), start=0):
        first_business_unit = batch[0]["SUBDIVISION"].strip()
        key = f"lb-{first_business_unit.lower()}-uat-{idx}"
        batches[key] = [row["HOSTNAME"].strip() for row in batch]

    # PROD batches
    for idx, batch in enumerate(batch_list(prod_rows, 10), start=0):
        first_business_unit = batch[0]["SUBDIVISION"].strip()
        key = f"lb-{first_business_unit.lower()}-prod-{idx}"
        batches[key] = [row["HOSTNAME"].strip() for row in batch]

    # Map origin pool name -> origin classification
    origin_pool_dict = {}
    for i in range(min(len(origin_pool_name), len(origin_classification))):
        origin_pool_dict[origin_pool_name[i]] = origin_classification[i]

    return batches, origin_classification, certificate_name, origin_pool_name, origin_pool_dict


# F5 XC Certificate Mapping

def get_f5_certificates(api_url, token, namespace):
    """Fetch F5 XC certificates and map certificate name -> list of SANs."""
    headers = {"Authorization": f"APIToken {token}"}
    response = requests.get(f"{api_url}/config/namespaces/{namespace}/certificates?report_fields", headers=headers)
    response.raise_for_status()
    all_details = response.json()
    actual = all_details.get("items", [])

    cert_to_sans = {}
    for item in actual:
        cert_name = item.get("name")  # Certificate name
        infos = item.get("get_spec", {}).get("infos", [])
        sans = []
        for info in infos:
            sans.extend(info.get("subject_alternative_names", []))
        cert_to_sans[cert_name] = sans
    return cert_to_sans

def get_domain(hostname):
    parts = hostname.split(".")
    if len(parts) < 2:
        return hostname  # just return as-is if not standard
    return ".".join(parts[-2:])

def map_hostnames_to_certs(batches, cert_to_sans):
    #hostname to cert static mapping
    hostname_cert_mapping = {}
    for hostnames in batches.values():
        for host in hostnames:
            host_lower = host.lower()
            matched_certs = [
                cert_name
                for cert_name, sans in cert_to_sans.items()
                if any(host_lower == san.lower() or (f"*.{get_domain(host_lower)}"==san.lower()) for san in sans) 
            ]
            hostname_cert_mapping[host] = matched_certs if matched_certs else ["NO_CERT"]
    return hostname_cert_mapping

def cert_per_lb():
    batches_2 = {
    lb: list(dict.fromkeys(hostname_cert_mapping[d][0] for d in domains))
    for lb, domains in batches.items()
    }
    return batches_2


def write_tfvars_file(
    tfvars_file_path,
    batches,
    origin_classification,
    certificate_name,
    origin_pool_name,
    origin_pool_dict,
    hostname_cert_mapping
):
    """Write outputs to Terraform .tfvars file."""
    with open(tfvars_file_path, "w") as f:
        f.write("batches = " + to_hcl_map(batches) + "\n\n")
        # f.write(f"batches_py = {json.dumps(batches, indent=2)}\n\n")
        f.write(f"origin_classification = {json.dumps(origin_classification, indent=2)}\n\n")
        f.write(f"cert_per_lb = {json.dumps(cert_per_lb(), indent=2)}\n\n")
        f.write(f"certificate_names = {json.dumps(certificate_name, indent=2)}\n\n")
        f.write(f"origin_pool_names = {json.dumps(origin_pool_name, indent=2)}\n\n")
        f.write(f"origin_pool_dict = {json.dumps(origin_pool_dict, indent=2)}\n\n")
        f.write(f"hostname_cert_mapping = {json.dumps(hostname_cert_mapping, indent=2)}\n\n")


if __name__ == "__main__":
    file_path = "<file_name>.csv"
    api_url = "<tenant api url>"
    token = api_key
    namespace = "<your namespace>"
    tfvars_file = "terraform.tfvars"

    # Step 1: Read and filter CSV
    filtered_rows = read_csv_first_9_columns_filtered(file_path)
    print(filtered_rows)
    # Step 2: Process CSV
    batches, origin_classification, certificate_name, origin_pool_name, origin_pool_dict = process_csv(filtered_rows)

    # Step 3: Fetch F5 XC certificates
    cert_to_sans = get_f5_certificates(api_url, token, namespace)

    # Step 4: Map hostnames to certs (case-insensitive)
    hostname_cert_mapping = map_hostnames_to_certs(batches, cert_to_sans)

    # Step 5: Write outputs to tfvars
    write_tfvars_file(
        tfvars_file,
        batches,
        origin_classification,
        certificate_name,
        origin_pool_name,
        origin_pool_dict,
        hostname_cert_mapping
    )

    print(f"\nTerraform tfvars file '{tfvars_file}' written successfully.")
