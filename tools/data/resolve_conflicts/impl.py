# tools/data/resolve_conflicts/impl.py - Smart conflict resolution using standard libraries

def execute(inputs, context):
    """Resolve conflicts in messy customer data using fuzzy matching and reconciliation"""

    try:
        import pandas as pd
        from fuzzywuzzy import fuzz, process
        import re
        import json
        from datetime import datetime
        import numpy as np
    except ImportError as e:
        return {"error": f"Required library not available: {e}. Install with: pip install pandas fuzzywuzzy python-levenshtein"}

    crm_data = inputs["crm_data"]
    support_data = inputs["support_data"]
    payment_data = inputs["payment_data"]
    confidence_threshold = inputs.get("confidence_threshold", 0.8)

    # Convert to pandas DataFrames
    crm_df = pd.DataFrame(crm_data["rows"], columns=crm_data["header"])

    # Handle support data (JSON format)
    if isinstance(support_data["rows"][0], dict):
        support_df = pd.DataFrame(support_data["rows"])
    else:
        support_df = pd.DataFrame(support_data["rows"], columns=support_data["header"])

    payment_df = pd.DataFrame(payment_data["rows"], columns=payment_data["header"])

    conflict_report = {
        "duplicates_found": 0,
        "conflicts_resolved": 0,
        "data_cleaned": 0,
        "records_reconciled": 0,
        "actions_taken": []
    }

    # 1. Clean and standardize CRM data
    crm_df = _clean_crm_data(crm_df, conflict_report)

    # 2. Find and merge duplicate customers
    unified_df = _resolve_duplicates(crm_df, confidence_threshold, conflict_report)

    # 3. Extract and reconcile support ticket customer info
    support_customers = _extract_support_customers(support_df, conflict_report)

    # 4. Reconcile with unified customer data
    unified_df = _reconcile_support_data(unified_df, support_customers, confidence_threshold, conflict_report)

    # 5. Match payment records to customers
    unified_df, orphaned_payments = _reconcile_payments(unified_df, payment_df, confidence_threshold, conflict_report)

    # 6. Generate actionable insights
    _add_actionable_insights(unified_df, conflict_report)

    return {
        "unified_customers": {
            "header": list(unified_df.columns),
            "rows": unified_df.fillna("").values.tolist()
        },
        "conflict_report": conflict_report,
        "orphaned_records": {
            "header": list(orphaned_payments.columns) if not orphaned_payments.empty else [],
            "rows": orphaned_payments.values.tolist() if not orphaned_payments.empty else []
        }
    }


def _clean_crm_data(df, report):
    """Clean and standardize CRM data formats"""
    df = df.copy()
    actions = []

    # Standardize phone numbers
    if 'phone' in df.columns:
        def clean_phone(phone):
            if pd.isna(phone) or phone == "":
                return ""
            # Remove all non-digits, then format
            digits = re.sub(r'\D', '', str(phone))
            if len(digits) == 10:
                return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
            elif len(digits) == 11 and digits[0] == '1':
                return f"({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
            else:
                return phone  # Keep invalid as-is for flagging

        original_phones = df['phone'].copy()
        df['phone'] = df['phone'].apply(clean_phone)
        cleaned_count = sum(original_phones != df['phone'])
        if cleaned_count > 0:
            actions.append(f"Standardized {cleaned_count} phone number formats")
            report["data_cleaned"] += cleaned_count

    # Validate and flag invalid emails
    if 'email' in df.columns:
        def is_valid_email(email):
            if pd.isna(email) or email == "":
                return True  # Empty is okay
            pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            return re.match(pattern, str(email)) is not None

        invalid_emails = df[~df['email'].apply(is_valid_email)]['email'].count()
        if invalid_emails > 0:
            actions.append(f"Flagged {invalid_emails} invalid email addresses")

    # Clean revenue data
    if 'revenue' in df.columns:
        def clean_revenue(revenue):
            if pd.isna(revenue) or revenue == "":
                return None
            if isinstance(revenue, (int, float)):
                return float(revenue)
            # Handle string formats
            cleaned = re.sub(r'[^\d.]', '', str(revenue))
            try:
                return float(cleaned) if cleaned else None
            except ValueError:
                return None

        original_revenue = df['revenue'].copy()
        df['revenue'] = df['revenue'].apply(clean_revenue)
        cleaned_count = sum((original_revenue != df['revenue']) & pd.notna(original_revenue))
        if cleaned_count > 0:
            actions.append(f"Cleaned {cleaned_count} revenue format issues")
            report["data_cleaned"] += cleaned_count

    report["actions_taken"].extend(actions)
    return df


def _resolve_duplicates(df, threshold, report):
    """Find and merge duplicate customers using fuzzy matching"""
    if df.empty:
        return df

    # Create customer signatures for matching
    def create_signature(row):
        name = str(row.get('name', '')).lower().strip()
        email = str(row.get('email', '')).lower().strip()
        company = str(row.get('company', '')).lower().strip()
        return f"{name}|{email}|{company}"

    df['_signature'] = df.apply(create_signature, axis=1)

    # Find potential duplicates using fuzzy matching
    duplicates_to_merge = []
    processed_indices = set()

    for i, row1 in df.iterrows():
        if i in processed_indices:
            continue

        current_group = [i]

        for j, row2 in df.iterrows():
            if j <= i or j in processed_indices:
                continue

            # Calculate similarity scores
            name_score = fuzz.ratio(str(row1['name']), str(row2['name'])) / 100.0
            email_score = fuzz.ratio(str(row1['email']), str(row2['email'])) / 100.0 if row1['email'] and row2['email'] else 0
            company_score = fuzz.ratio(str(row1['company']), str(row2['company'])) / 100.0 if row1['company'] and row2['company'] else 0

            # Weighted similarity (name is most important)
            overall_score = (name_score * 0.5) + (email_score * 0.3) + (company_score * 0.2)

            if overall_score >= threshold:
                current_group.append(j)

        if len(current_group) > 1:
            duplicates_to_merge.append(current_group)
            processed_indices.update(current_group)

    # Merge duplicate groups
    merged_df = df.copy()
    rows_to_drop = []

    for group in duplicates_to_merge:
        # Keep the first record, merge data from others
        primary_idx = group[0]
        merge_data = {}

        for idx in group:
            for col in df.columns:
                if col.startswith('_'):
                    continue
                value = df.loc[idx, col]
                if pd.notna(value) and value != "":
                    if col not in merge_data:
                        merge_data[col] = value
                    elif col == 'revenue':
                        # Take the highest revenue
                        try:
                            current_rev = float(merge_data.get(col, 0))
                            new_rev = float(value)
                            if new_rev > current_rev:
                                merge_data[col] = new_rev
                        except (ValueError, TypeError):
                            pass

        # Update primary record with merged data
        for col, value in merge_data.items():
            merged_df.loc[primary_idx, col] = value

        # Mark other records for removal
        rows_to_drop.extend(group[1:])

        report["duplicates_found"] += len(group) - 1
        report["conflicts_resolved"] += 1
        report["actions_taken"].append(f"Merged {len(group)} duplicate records for {merge_data.get('name', 'customer')}")

    # Remove duplicate rows
    merged_df = merged_df.drop(rows_to_drop)
    merged_df = merged_df.drop(columns=['_signature'], errors='ignore')

    return merged_df.reset_index(drop=True)


def _extract_support_customers(support_df, report):
    """Extract structured customer info from unstructured support tickets"""
    customers = []

    for _, ticket in support_df.iterrows():
        customer_info = {}

        # Extract customer name from various fields
        customer_text = str(ticket.get('customer', ''))
        email = str(ticket.get('email', ''))

        # Parse customer name from text like "John Smith from Acme Corp"
        name_patterns = [
            r'^([A-Za-z\s]+)\s+(?:from|at|-)\s+',  # "John Smith from Acme"
            r'^([A-Za-z\s]+)$'  # Just name
        ]

        extracted_name = ""
        company = ""

        for pattern in name_patterns:
            match = re.match(pattern, customer_text)
            if match:
                extracted_name = match.group(1).strip()
                # Extract company if present
                if 'from' in customer_text or 'at' in customer_text:
                    company_match = re.search(r'(?:from|at)\s+(.+)', customer_text)
                    if company_match:
                        company = company_match.group(1).strip()
                break

        if extracted_name and email:
            customer_info = {
                'name': extracted_name,
                'email': email,
                'company': company,
                'support_issues': 1,
                'last_contact': ticket.get('created', ''),
                'sentiment': ticket.get('sentiment', ''),
                'revenue_impact': ticket.get('revenue_impact', '')
            }
            customers.append(customer_info)

    if customers:
        report["actions_taken"].append(f"Extracted {len(customers)} customer profiles from support tickets")

    return pd.DataFrame(customers)


def _reconcile_support_data(crm_df, support_customers, threshold, report):
    """Match support customers with CRM data"""
    if support_customers.empty:
        return crm_df

    matched_count = 0

    for _, support_customer in support_customers.iterrows():
        # Find best match in CRM data
        best_match_idx = None
        best_score = 0

        for idx, crm_customer in crm_df.iterrows():
            name_score = fuzz.ratio(support_customer['name'], crm_customer['name']) / 100.0
            email_score = fuzz.ratio(support_customer['email'], crm_customer['email']) / 100.0 if crm_customer['email'] else 0

            overall_score = (name_score * 0.6) + (email_score * 0.4)

            if overall_score > best_score and overall_score >= threshold:
                best_score = overall_score
                best_match_idx = idx

        # Update CRM record with support data
        if best_match_idx is not None:
            # Add support-specific fields
            crm_df.loc[best_match_idx, 'support_issues'] = support_customer['support_issues']
            crm_df.loc[best_match_idx, 'sentiment'] = support_customer['sentiment']
            crm_df.loc[best_match_idx, 'revenue_impact'] = support_customer['revenue_impact']
            matched_count += 1
        else:
            # Add as new customer if no match found
            new_row = {col: "" for col in crm_df.columns}
            new_row.update(support_customer.to_dict())
            new_row['customer_id'] = f"SUP-{len(crm_df) + 1:03d}"
            crm_df = pd.concat([crm_df, pd.DataFrame([new_row])], ignore_index=True)

    if matched_count > 0:
        report["records_reconciled"] += matched_count
        report["actions_taken"].append(f"Reconciled {matched_count} support customers with CRM data")

    return crm_df


def _reconcile_payments(crm_df, payment_df, threshold, report):
    """Match payment records to customers"""
    orphaned = []
    matched_count = 0

    for _, payment in payment_df.iterrows():
        customer_ref = str(payment.get('customer_reference', ''))
        matched = False

        # Try exact customer ID match first
        if customer_ref in crm_df['customer_id'].values:
            idx = crm_df[crm_df['customer_id'] == customer_ref].index[0]
            _add_payment_info(crm_df, idx, payment)
            matched = True
            matched_count += 1
        else:
            # Try fuzzy matching on names
            best_match_idx = None
            best_score = 0

            for idx, customer in crm_df.iterrows():
                name_score = fuzz.ratio(customer_ref, customer['name']) / 100.0
                if name_score > best_score and name_score >= threshold:
                    best_score = name_score
                    best_match_idx = idx

            if best_match_idx is not None:
                _add_payment_info(crm_df, best_match_idx, payment)
                matched = True
                matched_count += 1

        if not matched:
            orphaned.append(payment.to_dict())

    if matched_count > 0:
        report["records_reconciled"] += matched_count
        report["actions_taken"].append(f"Matched {matched_count} payments to customers")

    if orphaned:
        report["actions_taken"].append(f"Found {len(orphaned)} orphaned payment records")

    return crm_df, pd.DataFrame(orphaned)


def _add_payment_info(df, idx, payment):
    """Add payment information to customer record"""
    if 'total_payments' not in df.columns:
        df['total_payments'] = 0.0
        df['last_payment_date'] = ""
        df['payment_status'] = ""

    try:
        amount = float(payment.get('amount', 0))
        current_total = float(df.loc[idx, 'total_payments'] or 0)
        df.loc[idx, 'total_payments'] = current_total + amount
        df.loc[idx, 'last_payment_date'] = payment.get('date', '')
        df.loc[idx, 'payment_status'] = payment.get('status', '')
    except (ValueError, TypeError):
        pass


def _add_actionable_insights(df, report):
    """Generate actionable business insights from reconciled data"""
    insights = []

    # Identify customers at risk
    if 'sentiment' in df.columns:
        angry_customers = df[df['sentiment'] == 'angry']
        if not angry_customers.empty:
            insights.append(f"URGENT: {len(angry_customers)} angry customers need immediate attention")

    # Revenue opportunities
    if 'revenue_impact' in df.columns:
        upsell_customers = df[df['revenue_impact'].str.contains('upsell', case=False, na=False)]
        if not upsell_customers.empty:
            insights.append(f"OPPORTUNITY: {len(upsell_customers)} customers interested in upgrades")

    # Payment issues
    if 'payment_status' in df.columns:
        failed_payments = df[df['payment_status'] == 'failed']
        if not failed_payments.empty:
            insights.append(f"ATTENTION: {len(failed_payments)} customers have failed payments")

    # Inactive customers
    if 'status' in df.columns:
        inactive_customers = df[df['status'] == 'inactive']
        if not inactive_customers.empty:
            total_revenue_at_risk = inactive_customers['revenue'].sum() if 'revenue' in df.columns else 0
            insights.append(f"RETENTION: {len(inactive_customers)} inactive customers (${total_revenue_at_risk:,.0f} revenue at risk)")

    report["actionable_insights"] = insights
    report["actions_taken"].extend([f"Generated insight: {insight}" for insight in insights])