# tools/data/cross_reference/impl.py - Enterprise data cross-referencing and validation

def execute(inputs, context):
    """Cross-reference data across multiple enterprise systems with intelligent validation"""

    try:
        import pandas as pd
        from fuzzywuzzy import fuzz
        import numpy as np
        import re
        from datetime import datetime
    except ImportError as e:
        return {"error": f"Required library not available: {e}. Install with: pip install pandas fuzzywuzzy"}

    primary_source = inputs["primary_source"]
    reference_sources = inputs.get("reference_sources", [])
    match_fields = inputs.get("match_fields", ["id", "email", "name"])
    validation_rules = inputs.get("validation_rules", {})

    # Convert primary source to DataFrame
    primary_df = pd.DataFrame(primary_source["rows"], columns=primary_source["header"])

    # Initialize results
    discrepancies = []
    confidence_scores = {}
    validated_df = primary_df.copy()

    # Process each reference source
    for ref_idx, ref_source in enumerate(reference_sources):
        ref_df = pd.DataFrame(ref_source["rows"], columns=ref_source["header"])

        # Cross-reference and validate
        ref_discrepancies, ref_confidence = _cross_reference_source(
            validated_df, ref_df, match_fields, validation_rules, ref_idx
        )

        discrepancies.extend(ref_discrepancies)
        confidence_scores.update(ref_confidence)

    # Calculate overall confidence scores
    overall_confidence = _calculate_overall_confidence(validated_df, confidence_scores)

    # Apply intelligent corrections based on confidence
    validated_df = _apply_intelligent_corrections(validated_df, discrepancies, overall_confidence)

    return {
        "validated_data": {
            "header": list(validated_df.columns),
            "rows": validated_df.fillna("").values.tolist()
        },
        "discrepancies": discrepancies,
        "confidence_scores": overall_confidence
    }


def _cross_reference_source(primary_df, ref_df, match_fields, validation_rules, source_idx):
    """Cross-reference primary data against a reference source"""
    discrepancies = []
    confidence_scores = {}

    # Find matching records using multiple field strategies
    for primary_idx, primary_row in primary_df.iterrows():
        matches = _find_matches(primary_row, ref_df, match_fields)
        record_key = f"record_{primary_idx}"

        if not matches:
            # No matches found
            discrepancies.append({
                "type": "missing_reference",
                "primary_record": primary_idx,
                "source": f"reference_{source_idx}",
                "description": f"No matching record found in reference source {source_idx}",
                "severity": "medium",
                "recommended_action": "Verify record existence or check for data entry errors"
            })
            confidence_scores[record_key] = confidence_scores.get(record_key, 1.0) * 0.8
        else:
            # Validate against best match
            best_match = matches[0]  # Assuming sorted by confidence
            ref_row = ref_df.iloc[best_match["index"]]

            # Check for data inconsistencies
            field_discrepancies = _validate_record_consistency(
                primary_row, ref_row, validation_rules, primary_idx, source_idx
            )

            discrepancies.extend(field_discrepancies)

            # Calculate confidence based on match quality and consistency
            match_confidence = best_match["confidence"]
            consistency_score = 1.0 - (len(field_discrepancies) * 0.1)  # Reduce by 10% per discrepancy

            overall_record_confidence = match_confidence * consistency_score
            confidence_scores[record_key] = confidence_scores.get(record_key, 1.0) * overall_record_confidence

    return discrepancies, confidence_scores


def _find_matches(primary_row, ref_df, match_fields):
    """Find potential matches using fuzzy matching on specified fields"""
    matches = []

    for ref_idx, ref_row in ref_df.iterrows():
        total_score = 0.0
        valid_fields = 0

        # Score each matching field
        for field in match_fields:
            if field in primary_row.index and field in ref_row.index:
                primary_val = str(primary_row[field]).strip().lower()
                ref_val = str(ref_row[field]).strip().lower()

                if primary_val and ref_val and primary_val != "nan" and ref_val != "nan":
                    if field in ['id', 'customer_id']:
                        # Exact match for IDs
                        field_score = 1.0 if primary_val == ref_val else 0.0
                    elif field == 'email':
                        # High precision for emails
                        field_score = fuzz.ratio(primary_val, ref_val) / 100.0
                        # Bonus for exact domain match
                        if '@' in primary_val and '@' in ref_val:
                            p_domain = primary_val.split('@')[1]
                            r_domain = ref_val.split('@')[1]
                            if p_domain == r_domain:
                                field_score = min(1.0, field_score + 0.2)
                    else:
                        # Fuzzy match for names and other fields
                        field_score = fuzz.token_sort_ratio(primary_val, ref_val) / 100.0

                    total_score += field_score
                    valid_fields += 1

        if valid_fields > 0:
            avg_score = total_score / valid_fields
            if avg_score > 0.6:  # Minimum threshold for potential match
                matches.append({
                    "index": ref_idx,
                    "confidence": avg_score,
                    "matched_fields": valid_fields
                })

    # Sort by confidence descending
    matches.sort(key=lambda x: x["confidence"], reverse=True)
    return matches


def _validate_record_consistency(primary_row, ref_row, validation_rules, primary_idx, source_idx):
    """Validate consistency between primary and reference records"""
    discrepancies = []

    # Common field validations
    common_fields = set(primary_row.index) & set(ref_row.index)

    for field in common_fields:
        primary_val = primary_row[field]
        ref_val = ref_row[field]

        # Skip empty values
        if pd.isna(primary_val) or pd.isna(ref_val) or primary_val == "" or ref_val == "":
            continue

        # Apply field-specific validation
        field_discrepancy = None

        if field in ['revenue', 'amount', 'total_payments']:
            # Numeric field validation
            field_discrepancy = _validate_numeric_field(
                field, primary_val, ref_val, primary_idx, source_idx
            )
        elif field in ['email']:
            # Email validation
            field_discrepancy = _validate_email_field(
                field, primary_val, ref_val, primary_idx, source_idx
            )
        elif field in ['phone']:
            # Phone validation
            field_discrepancy = _validate_phone_field(
                field, primary_val, ref_val, primary_idx, source_idx
            )
        elif field in ['status']:
            # Status validation
            field_discrepancy = _validate_status_field(
                field, primary_val, ref_val, primary_idx, source_idx
            )
        else:
            # Generic string validation
            similarity = fuzz.ratio(str(primary_val).lower(), str(ref_val).lower()) / 100.0
            if similarity < 0.8:
                field_discrepancy = {
                    "type": "value_mismatch",
                    "field": field,
                    "primary_record": primary_idx,
                    "source": f"reference_{source_idx}",
                    "primary_value": str(primary_val),
                    "reference_value": str(ref_val),
                    "similarity": round(similarity, 2),
                    "severity": "low" if similarity > 0.5 else "medium",
                    "recommended_action": f"Review {field} values for potential data entry differences"
                }

        if field_discrepancy:
            discrepancies.append(field_discrepancy)

    # Apply custom validation rules
    for rule_name, rule_config in validation_rules.items():
        rule_result = _apply_custom_validation(rule_name, rule_config, primary_row, ref_row, primary_idx, source_idx)
        if rule_result:
            discrepancies.append(rule_result)

    return discrepancies


def _validate_numeric_field(field, primary_val, ref_val, primary_idx, source_idx):
    """Validate numeric fields with tolerance"""
    try:
        p_num = float(str(primary_val).replace('$', '').replace(',', ''))
        r_num = float(str(ref_val).replace('$', '').replace(',', ''))

        # Allow 5% tolerance for rounding differences
        tolerance = max(abs(p_num), abs(r_num)) * 0.05
        diff = abs(p_num - r_num)

        if diff > tolerance and diff > 1.0:  # Ignore tiny differences
            severity = "high" if diff > max(abs(p_num), abs(r_num)) * 0.1 else "medium"
            return {
                "type": "numeric_mismatch",
                "field": field,
                "primary_record": primary_idx,
                "source": f"reference_{source_idx}",
                "primary_value": p_num,
                "reference_value": r_num,
                "difference": round(diff, 2),
                "severity": severity,
                "recommended_action": f"Investigate {field} discrepancy - possible data sync issue"
            }
    except (ValueError, TypeError):
        return {
            "type": "numeric_format_error",
            "field": field,
            "primary_record": primary_idx,
            "source": f"reference_{source_idx}",
            "primary_value": str(primary_val),
            "reference_value": str(ref_val),
            "severity": "medium",
            "recommended_action": f"Fix numeric format for {field}"
        }

    return None


def _validate_email_field(field, primary_val, ref_val, primary_idx, source_idx):
    """Validate email field consistency"""
    p_email = str(primary_val).lower().strip()
    r_email = str(ref_val).lower().strip()

    if p_email != r_email:
        # Check if it's just domain differences (common in enterprise)
        p_parts = p_email.split('@')
        r_parts = r_email.split('@')

        if len(p_parts) == 2 and len(r_parts) == 2:
            if p_parts[0] == r_parts[0]:  # Same username, different domain
                return {
                    "type": "email_domain_mismatch",
                    "field": field,
                    "primary_record": primary_idx,
                    "source": f"reference_{source_idx}",
                    "primary_value": p_email,
                    "reference_value": r_email,
                    "severity": "low",
                    "recommended_action": "Verify which email domain is current"
                }

        return {
            "type": "email_mismatch",
            "field": field,
            "primary_record": primary_idx,
            "source": f"reference_{source_idx}",
            "primary_value": p_email,
            "reference_value": r_email,
            "severity": "medium",
            "recommended_action": "Verify correct email address"
        }

    return None


def _validate_phone_field(field, primary_val, ref_val, primary_idx, source_idx):
    """Validate phone field with format normalization"""
    # Normalize phone numbers to digits only
    p_digits = re.sub(r'\D', '', str(primary_val))
    r_digits = re.sub(r'\D', '', str(ref_val))

    # Remove country code if present
    if len(p_digits) == 11 and p_digits.startswith('1'):
        p_digits = p_digits[1:]
    if len(r_digits) == 11 and r_digits.startswith('1'):
        r_digits = r_digits[1:]

    if p_digits != r_digits and len(p_digits) == 10 and len(r_digits) == 10:
        return {
            "type": "phone_mismatch",
            "field": field,
            "primary_record": primary_idx,
            "source": f"reference_{source_idx}",
            "primary_value": str(primary_val),
            "reference_value": str(ref_val),
            "severity": "medium",
            "recommended_action": "Verify correct phone number"
        }

    return None


def _validate_status_field(field, primary_val, ref_val, primary_idx, source_idx):
    """Validate status field consistency"""
    p_status = str(primary_val).lower().strip()
    r_status = str(ref_val).lower().strip()

    # Map common status variations
    status_mappings = {
        'active': ['active', 'current', 'live'],
        'inactive': ['inactive', 'suspended', 'paused'],
        'closed': ['closed', 'terminated', 'ended']
    }

    # Check if statuses are equivalent
    p_normalized = None
    r_normalized = None

    for standard, variations in status_mappings.items():
        if p_status in variations:
            p_normalized = standard
        if r_status in variations:
            r_normalized = standard

    if p_normalized != r_normalized:
        severity = "high" if (p_normalized == 'active') != (r_normalized == 'active') else "medium"
        return {
            "type": "status_mismatch",
            "field": field,
            "primary_record": primary_idx,
            "source": f"reference_{source_idx}",
            "primary_value": str(primary_val),
            "reference_value": str(ref_val),
            "severity": severity,
            "recommended_action": f"Reconcile status difference - may impact billing/access"
        }

    return None


def _apply_custom_validation(rule_name, rule_config, primary_row, ref_row, primary_idx, source_idx):
    """Apply custom validation rules defined by user"""
    # Placeholder for extensible validation rules
    # Users can define custom rules in the validation_rules input
    return None


def _calculate_overall_confidence(df, confidence_scores):
    """Calculate overall confidence scores for all records"""
    overall_confidence = {}

    for idx in range(len(df)):
        record_key = f"record_{idx}"
        # Start with base confidence, modified by cross-reference results
        base_confidence = confidence_scores.get(record_key, 1.0)

        # Adjust based on data completeness
        completeness = _calculate_record_completeness(df.iloc[idx])
        overall_confidence[record_key] = {
            "cross_reference_score": round(base_confidence, 2),
            "completeness_score": round(completeness, 2),
            "overall_score": round((base_confidence * 0.7) + (completeness * 0.3), 2)
        }

    return overall_confidence


def _calculate_record_completeness(record):
    """Calculate how complete a record is (0.0 to 1.0)"""
    total_fields = len(record)
    filled_fields = sum(1 for val in record if pd.notna(val) and str(val).strip() != "")
    return filled_fields / total_fields if total_fields > 0 else 0.0


def _apply_intelligent_corrections(df, discrepancies, confidence_scores):
    """Apply intelligent corrections based on discrepancy analysis"""
    corrected_df = df.copy()

    # Group discrepancies by record and field
    corrections_applied = 0

    # For now, just add a validation flag column
    corrected_df['_validation_flags'] = ""

    for idx in range(len(corrected_df)):
        record_key = f"record_{idx}"
        confidence = confidence_scores.get(record_key, {})

        # Flag records with low confidence
        if confidence.get('overall_score', 1.0) < 0.7:
            corrected_df.loc[idx, '_validation_flags'] = "low_confidence"
            corrections_applied += 1

    # Could add more sophisticated correction logic here
    # For example: auto-correct phone number formats, email domains, etc.

    return corrected_df