# XC Scalable Naming — Origin Pool & Load Balancer Automation

> Automate the creation of ** Distributed Cloud (XC)** Origin Pools, custom-certificate HTTPS Load Balancers, and routes — driven entirely from a CSV file and Terraform.

---

## Table of Contents

- [Overview](#overview)
- [Architecture & Data Flow](#architecture--data-flow)
- [Repository Structure](#repository-structure)
- [How It Works — Step-by-Step](#how-it-works--step-by-step)
  - [Step 1 — CSV Cleaning (`cleaning_csv.py`)](#step-1--csv-cleaning-cleaning_csvpy)
  - [Step 2 — Variable Extraction & tfvars Generation (`csv_extraction_var.py`)](#step-2--variable-extraction--tfvars-generation-csv_extraction_varpy)
  - [Step 3 — Terraform Execution](#step-3--terraform-execution)
  - [Step 4 — Terraform Modules](#step-4--terraform-modules)
- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
- [Usage](#usage)
- [CSV Format](#csv-format)
- [Generated `terraform.tfvars` Structure](#generated-terraformtfvars-structure)
- [Terraform Variables Reference](#terraform-variables-reference)
- [Important Notes & Customization Points](#important-notes--customization-points)

---

## Overview

Managing large numbers of hostnames, origin pools, and HTTPS load balancers on F5 XC manually is error-prone and doesn't scale. This project bridges a simple CSV spreadsheet (your source of truth) with Terraform by:

1. **Parsing and cleaning** a raw CSV export of your application inventory.
2. **Querying the XC API** for existing certificates and matching SANs to hostnames automatically.
3. **Writing a `terraform.tfvars`** file populated with all derived variables.
4. **Applying Terraform** to create origin pools, HTTPS LBs (with custom certs), and routes in XC — all in one shot.

---

## Architecture & Data Flow

```
  your-data.csv
       │
       ▼
┌─────────────────────┐
│  cleaning_csv.py    │  ← strips BOM, drops unwanted columns,
│                     │    keeps first 9 columns only
└────────┬────────────┘
         │  filtered rows (list of dicts)
         ▼
┌──────────────────────────┐
│  csv_extraction_var.py   │  ← main orchestrator
│                          │
│  1. process_csv()        │  → batches (≤10 hostnames/LB, split UAT/PROD)
│  2. get_f5_certificates()│  → calls XC REST API, fetches cert SANs
│  3. map_hostnames_to_    │  → wildcard + exact SAN matching
│     certs()              │
│  4. write_tfvars_file()  │  → writes terraform.tfvars in HCL format
└────────┬─────────────────┘
         │  terraform.tfvars
         ▼
┌─────────────────────────────────────────┐
│  Terraform                              │
│                                         │
│  provider.tf  → volterraedge/volterra   │
│  variables.tf → declares all inputs     │
│  main.tf      → calls two modules:      │
│    ├─ module "origin_pool"              │
│    └─ module "https_custom_lb"          │
│         └─ (depends_on origin_pool)     │
└─────────────────────────────────────────┘
         │
         ▼
   F5 Distributed Cloud
   ┌────────────────┐    ┌──────────────────────┐
   │  Origin Pools  │◄───│  HTTPS Custom LBs    │
   │  (per hostname)│    │  (per batch, ≤10 SAN)│
   └────────────────┘    └──────────────────────┘
```

---

## Repository Structure

```
.
├── cleaning_csv.py          # Step 1: CSV ingestion & cleaning
├── csv_extraction_var.py    # Step 2: Orchestrator — extracts vars, hits XC API, writes tfvars
├── tf_vars_actual_write.py  # Helper: HCL serialization & file writing
├── provider.tf              # Terraform provider config (volterraedge/volterra)
├── variables.tf             # All Terraform input variable declarations
├── main.tf                  # Root module — calls origin_pool & https_custom_lb
├── data.tf                  # Terraform data sources
├── modules/
│   ├── origin_pool/         # Creates XC origin pool resources
│   └── https_custom_lb/     # Creates XC HTTPS LBs with custom certs & routes
└── environments/            # (Optional) per-environment tfvars overrides
```

---

## How It Works — Step-by-Step

### Step 1 — CSV Cleaning (`cleaning_csv.py`)

**Entry point:** `read_csv_first_9_columns_filtered(file_path)`

This function is the very first thing that runs. It:

- Opens the CSV with `utf-8-sig` encoding to safely strip any **BOM character** (`\ufeff`) that Microsoft Excel commonly prepends.
- Reads the file using `csv.DictReader` so each row is a named dictionary.
- Trims the column list to the **first 9 columns** of your CSV — everything beyond that is ignored.
- Drops any additional columns you explicitly list in `remove_columns` (customized per your CSV schema).
- Returns a **list of dicts**, one per row, ready for the next stage.

```python
# Customize this to match your CSV before running
remove_columns = "<based on your csv>"
```

---

### Step 2 — Variable Extraction & tfvars Generation (`csv_extraction_var.py`)

This is the main orchestrator. Run it directly: `python csv_extraction_var.py`

It calls the cleaned rows from Step 1 and then executes four internal stages:

#### Stage A — `process_csv(rows)`

Iterates every row and produces:

| Output | What it is |
|---|---|
| `batches` | Dict of LB-name → list of hostnames, capped at **10 per LB** |
| `origin_classification` | Per-origin: `private_ip` or `private_name` (detected by whether the origin contains letters) |
| `certificate_names` | Hostname with dots replaced by dashes (e.g. `app.example.com` → `app-example-com`) |
| `origin_pool_names` | Derived as `<part1>-<part2>-origin` from the first two segments of the hostname |
| `origin_pool_dict` | Maps each origin pool name to its classified origin |

**Batching logic:** Rows are split by environment (`PROD/UAT` column). Within each environment, they are chunked into groups of 10 and named using the pattern:
```
lb-<subdivision>-<env>-<batch_index>
```
This naming ensures each LB stays within XC's SAN limits.

#### Stage B — `get_f5_certificates(api_url, token, namespace)`

Hits the XC REST API:
```
GET {api_url}/config/namespaces/{namespace}/certificates?report_fields
```
Returns a dict of `cert_name → [list of SANs]`, pulling `subject_alternative_names` from each certificate's `get_spec.infos`.

#### Stage C — `map_hostnames_to_certs(batches, cert_to_sans)`

For every hostname in every batch, performs a **case-insensitive** SAN lookup supporting both:
- **Exact match**: `app.example.com == app.example.com`
- **Wildcard match**: `*.example.com` covers any hostname on that domain

If no cert is found, the hostname is tagged `NO_CERT` so you can catch gaps before applying.

#### Stage D — `write_tfvars_file(...)`

Serializes all derived variables into `terraform.tfvars` in valid HCL format using the `to_hcl_map()` helper (which handles nested dicts, lists, and strings). The file becomes Terraform's sole input — no manual editing required.

---

### Step 3 — Terraform Execution

Once `terraform.tfvars` is generated, run the standard Terraform workflow:

```bash
# Initialize providers and modules
terraform init

# Preview what will be created
terraform plan

# Apply — creates origin pools first, then LBs
terraform apply
```

The `api_token`, `namespace`, `tenant_url`, and `tenant` are expected as **environment variables** (not in the tfvars file) to avoid committing secrets:

```bash
export TF_VAR_api_token="your-xc-api-token"
export TF_VAR_namespace="your-namespace"
export TF_VAR_tenant_url="https://your-tenant.console.ves.volterra.io/api"
export TF_VAR_tenant="your-tenant-name"
```

---

### Step 4 — Terraform Modules

#### `module "origin_pool"` (`./modules/origin_pool`)

Runs **first** (no dependencies). Creates one XC origin pool per entry in `origin_pool_names`, using:
- `origin_pool_dict` to determine whether to configure the origin as a private IP or private DNS name
- `origin_classification` for the type flag passed to the volterra provider

#### `module "https_custom_lb"` (`./modules/https_custom_lb`)

Runs **after** origin pools are created (`depends_on = [module.origin_pool]`). For each batch:
- Creates an HTTPS LB with the matching custom certificate (from `cert_per_lb`)
- Attaches the appropriate origin pools
- Configures per-hostname routes based on `hostname_cert_mapping`

**Output:** `custom_lb_list` — a list of all LBs created in the namespace.

---

## Prerequisites

- Python 3.8+
- `pip install python-dotenv requests`
- Terraform >= 0.13.1
- A valid F5 XC tenant with:
  - An API token with read access to certificates and write access to origin pools / LBs
  - A `.p12` certificate file for Terraform provider authentication
  - Pre-existing TLS certificates uploaded to your namespace

---

## Configuration

### `.env` file (for the Python scripts)

```env
TF_VAR_api_token=your_xc_api_token_here
```

### `provider.tf` (update before running Terraform)

```hcl
provider "volterra" {
  api_p12_file = "/path/to/your/credential.p12"
  url          = var.tenant_url
}
```

---

## Usage

```bash
# 1. Install Python dependencies
pip install python-dotenv requests

# 2. Set your secrets
cp .env.example .env
# Edit .env with your XC API token

# 3. Edit csv_extraction_var.py — fill in the placeholders:
#    file_path  = "your-data.csv"
#    api_url    = "https://<tenant>.console.ves.volterra.io/api"
#    namespace  = "your-namespace"
#    tfvars_file = "terraform.tfvars"

# 4. Run the Python pipeline
python csv_extraction_var.py
# → generates terraform.tfvars

# 5. Export Terraform env vars
export TF_VAR_api_token="..."
export TF_VAR_namespace="your-namespace"
export TF_VAR_tenant_url="https://<tenant>.console.ves.volterra.io/api"
export TF_VAR_tenant="your-tenant"

# 6. Update provider.tf with your .p12 path

# 7. Run Terraform
terraform init
terraform plan
terraform apply
```

---

## CSV Format

The script expects a CSV with **at minimum** these column headers (column order matters — only the first 9 are kept):

| Column | Description |
|---|---|
| `SUBDIVISION` | Business unit / team name (used in LB naming) |
| `PROD/UAT` | Environment — must be exactly `prod` or `uat` (case-insensitive) |
| `HOSTNAME` | Fully qualified hostname (e.g. `app.example.com`) |
| `ORIGIN IP / FQDN` | Backend origin — IP address or DNS name |

> **Tip:** If your CSV has a BOM or extra columns exported from Excel, `cleaning_csv.py` handles both automatically.

---

## Generated `terraform.tfvars` Structure

After running the Python script, `terraform.tfvars` will contain:

```hcl
batches = {
  lb-payments-prod-0 = ["app1.example.com", "app2.example.com", ...]
  lb-payments-uat-0  = ["uat-app1.example.com", ...]
}

origin_classification = [
  ["10.0.0.1", "private_ip"],
  ["backend.internal.example.com", "private_name"],
  ...
]

cert_per_lb = {
  "lb-payments-prod-0" = ["wildcard-example-com"]
}

certificate_names     = ["app1-example-com", "app2-example-com", ...]
origin_pool_names     = ["app1-example-origin", "app2-example-origin", ...]
origin_pool_dict      = { "app1-example-origin" = ["10.0.0.1", "private_ip"] }
hostname_cert_mapping = { "app1.example.com" = ["wildcard-example-com"] }
```

---

## Terraform Variables Reference

| Variable | Type | Description |
|---|---|---|
| `api_token` | `string` (sensitive) | XC API token — set via `TF_VAR_api_token` |
| `namespace` | `string` | XC namespace to deploy into |
| `tenant_url` | `string` | XC tenant API base URL |
| `tenant` | `string` | XC tenant name |
| `batches` | `map(list(string))` | LB name → list of hostnames |
| `origin_classification` | `list(list(string))` | Origin address + type pairs |
| `certificate_names` | `list(string)` | Dash-formatted cert names |
| `origin_pool_names` | `list(string)` | Derived origin pool names |
| `origin_pool_dict` | `map(list(string))` | Pool name → [origin, type] |
| `hostname_cert_mapping` | `map(list(string))` | Hostname → matched cert names |
| `cert_per_lb` | `map(list(string))` | LB name → deduplicated cert list |

---

## Important Notes & Customization Points

Before running, you **must** update these placeholders in the code:

| File | Placeholder | What to set |
|---|---|---|
| `cleaning_csv.py` | `remove_columns = "<based on your csv>"` | Column name(s) to drop from your CSV |
| `csv_extraction_var.py` | `file_path = "<file_name>.csv"` | Path to your actual CSV file |
| `csv_extraction_var.py` | `api_url = "<tenant api url>"` | Your XC tenant API base URL |
| `csv_extraction_var.py` | `namespace = "<your namespace>"` | Your XC namespace |
| `provider.tf` | `api_p12_file = "<path to your p12 file>"` | Path to your XC .p12 credential file |

**Batch size:** The script hard-codes 10 hostnames per LB batch (`batch_size=10`). Adjust this in `batch_list()` inside `csv_extraction_var.py` if needed.

**`NO_CERT` hostnames:** If any hostname resolves to `NO_CERT` in `hostname_cert_mapping`, the corresponding certificate does not exist in XC yet. Upload it before running `terraform apply`.
