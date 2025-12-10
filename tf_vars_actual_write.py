import json

def write_tfvars_file(
    tfvars_file_path,
    batches,
    origin_classification,
    certificate_name,
    origin_pool_name,
    origin_pool_dict,
    hostname_cert_mapping
):
    
    # Python outputs written to a .tfvars file + converting python dict to hcl map
    with open(tfvars_file_path, "w") as f:
        f.write(f"batches = {json.dumps(batches, indent=2)}\n\n")
        f.write(f"origin_classification = {json.dumps(origin_classification, indent=2)}\n\n")
        f.write(f"certificate_names = {json.dumps(certificate_name, indent=2)}\n\n")
        f.write(f"origin_pool_names = {json.dumps(origin_pool_name, indent=2)}\n\n")
        f.write(f"origin_pool_dict = {json.dumps(origin_pool_dict, indent=2)}\n\n")
        f.write(f"hostname_cert_mapping = {json.dumps(hostname_cert_mapping, indent=2)}\n\n")

