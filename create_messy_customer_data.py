#!/usr/bin/env python3
"""Create realistic messy customer data for demo"""

import csv
import json
import random
from pathlib import Path

def create_messy_customer_database():
    """Create a chaotic customer database with real-world mess"""

    # Ensure sandbox directories exist
    Path("sandbox/in").mkdir(parents=True, exist_ok=True)

    # Different data sources with conflicting formats and information

    # Source 1: CRM Export (CSV) - some missing data, inconsistent formats
    crm_data = [
        ["customer_id", "name", "email", "phone", "company", "revenue", "status", "last_contact"],
        ["CUST001", "John Smith", "j.smith@acme.com", "(555) 123-4567", "Acme Corp", "50000", "active", "2024-01-15"],
        ["CUST002", "Sarah Johnson", "sarah@techflow.io", "555-987-6543", "TechFlow Inc", "75000", "active", "2024-01-20"],
        ["CUST003", "Mike Davis", "mike.davis@email.com", "", "DataSys LLC", "25000", "inactive", "2023-12-01"],
        ["CUST004", "Lisa Chen", "", "555.444.3333", "InnovateCorp", "", "active", ""],
        ["CUST005", "Robert Wilson", "rwilson@megacorp.com", "(555) 111-2222", "MegaCorp Industries", "120000", "potential", "2024-01-25"],
        ["CUST002", "Sarah J Johnson", "s.johnson@techflow.io", "5559876543", "TechFlow Inc", "78000", "active", "2024-01-22"],  # Duplicate with slight differences
        ["CUST006", "Anna Martinez", "anna@startupx.com", "555-333-4444", "", "15000", "active", "2024-01-18"],
        ["CUST007", "David Brown", "d.brown@invalid-email", "not-a-phone", "Brown Consulting", "invalid", "unknown", "never"],
    ]

    # Source 2: Support Tickets (JSON) - unstructured, conflicting customer info
    support_tickets = [
        {
            "ticket_id": "SUP-001",
            "customer": "John Smith from Acme Corp",
            "email": "johnsmith@acme.com",  # Different email format
            "issue": "Integration API failing with 500 errors since last week",
            "priority": "high",
            "created": "2024-01-16T10:30:00Z",
            "revenue_impact": "$2000 daily loss",
            "sentiment": "frustrated"
        },
        {
            "ticket_id": "SUP-002",
            "customer": "Sarah at TechFlow",
            "email": "sarah@techflow.io",
            "issue": "Dashboard shows wrong metrics, numbers don't match reports",
            "priority": "medium",
            "created": "2024-01-21T14:15:00Z",
            "revenue_impact": "minimal",
            "sentiment": "concerned"
        },
        {
            "ticket_id": "SUP-003",
            "customer": "Mike from DataSys",
            "email": "mike.davis@datasys.com",  # Different domain
            "issue": "Account was suspended but we paid the invoice",
            "priority": "urgent",
            "created": "2024-01-12T09:00:00Z",
            "revenue_impact": "account at risk",
            "sentiment": "angry"
        },
        {
            "ticket_id": "SUP-004",
            "customer": "Lisa Chen - InnovateCorp",
            "email": "l.chen@innovate.corp",  # Different domain format
            "issue": "Need pricing for enterprise plan upgrade",
            "priority": "low",
            "created": "2024-01-19T16:45:00Z",
            "revenue_impact": "potential upsell $50k",
            "sentiment": "interested"
        }
    ]

    # Source 3: Payment Records (CSV) - financial data with conflicts
    payment_data = [
        ["transaction_id", "customer_reference", "amount", "date", "status", "method", "notes"],
        ["TXN-001", "CUST001", "4166.67", "2024-01-01", "completed", "credit_card", "Monthly subscription"],
        ["TXN-002", "CUST002", "6250.00", "2024-01-01", "completed", "bank_transfer", "Quarterly payment"],
        ["TXN-003", "CUST005", "10000.00", "2024-01-15", "pending", "wire_transfer", "Initial deposit"],
        ["TXN-004", "CUST003", "2083.33", "2023-12-01", "failed", "credit_card", "Card declined"],
        ["TXN-005", "CUST006", "1250.00", "2024-01-18", "completed", "paypal", "Startup discount applied"],
        ["TXN-006", "Sarah TechFlow", "6500.00", "2024-01-22", "completed", "check", ""],  # Name instead of ID
        ["TXN-007", "CUST999", "5000.00", "2024-01-20", "completed", "credit_card", "Customer ID not in CRM"],
    ]

    # Save all data sources
    with open("sandbox/in/crm_customers.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(crm_data)

    with open("sandbox/in/support_tickets.json", "w", encoding="utf-8") as f:
        json.dump(support_tickets, f, indent=2)

    with open("sandbox/in/payment_records.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(payment_data)

    print("Created messy customer database with realistic problems:")
    print(f"  [OK] CRM data: {len(crm_data)-1} customers (with duplicates and missing data)")
    print(f"  [OK] Support tickets: {len(support_tickets)} unstructured tickets")
    print(f"  [OK] Payment records: {len(payment_data)-1} transactions (with orphaned records)")
    print()
    print("Realistic problems included:")
    print("  - Duplicate customers with slight name/email differences")
    print("  - Missing phone numbers, emails, revenue data")
    print("  - Inconsistent phone number formats")
    print("  - Invalid email addresses and phone numbers")
    print("  - Conflicting customer information across sources")
    print("  - Unstructured support ticket data")
    print("  - Orphaned payment records")
    print("  - Revenue data in multiple formats")
    print("  - Date formatting inconsistencies")

def create_conflicting_sales_data():
    """Create sales data with conflicts for decision-making demo"""

    # Sales data with missing values, outliers, and conflicts
    sales_data = [
        ["deal_id", "customer", "sales_rep", "amount", "stage", "close_date", "confidence", "notes"],
        ["DEAL001", "CUST001", "Alice Johnson", "25000", "proposal", "2024-02-15", "80", "Strong interest, budget approved"],
        ["DEAL002", "CUST002", "Bob Smith", "45000", "negotiation", "2024-02-20", "60", "Price sensitive, competitor evaluation"],
        ["DEAL003", "CUST005", "Alice Johnson", "100000", "verbal", "2024-02-10", "90", "Ready to sign, legal review"],
        ["DEAL004", "CUST006", "Charlie Brown", "8000", "proposal", "2024-03-01", "40", "Budget concerns, may delay"],
        ["DEAL005", "Unknown Customer", "Alice Johnson", "75000", "discovery", "", "30", "Lead from conference"],
        ["DEAL006", "CUST002", "Bob Smith", "52000", "negotiation", "2024-02-25", "", "Follow up needed"],  # Conflict with DEAL002
        ["DEAL007", "CUST001", "Dave Wilson", "30000", "closed-won", "2024-01-30", "100", ""],  # Different rep, different amount
        ["DEAL008", "CUST999", "Alice Johnson", "invalid_amount", "proposal", "2024-02-28", "70", "New customer, no CRM record"],
    ]

    with open("sandbox/in/sales_pipeline.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(sales_data)

    print(f"  [OK] Sales pipeline: {len(sales_data)-1} deals (with conflicts and missing data)")

if __name__ == "__main__":
    create_messy_customer_database()
    create_conflicting_sales_data()
    print()
    print("Ready for messy data demo! Use:")
    print("  aiox prompt --goal 'Clean and analyze customer database conflicts'")
    print("  aiox prompt --goal 'Identify revenue at risk from support tickets'")
    print("  aiox prompt --goal 'Reconcile payment records with customer data'")