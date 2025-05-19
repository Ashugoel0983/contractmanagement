#!/usr/bin/env python3
"""
API Testing Script for Contract Management System

This script provides utilities for testing the API endpoints.
It simulates API requests and displays the responses.

Usage: python api_test.py [endpoint]
"""

import os
import sys
import json
import argparse
import requests
from datetime import datetime, timedelta

# Base URL for API endpoints
BASE_URL = "http://localhost:5000/v1"

def test_health():
    """Test the health endpoint"""
    print("Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

def test_contracts_list():
    """Test the contracts list endpoint"""
    print("Testing contracts list endpoint...")
    response = requests.get(f"{BASE_URL}/contracts")
    print(f"Status code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Total contracts: {data['pagination']['total']}")
        for i, contract in enumerate(data['contracts']):
            print(f"\nContract {i+1}:")
            print(f"  Title: {contract['title']}")
            print(f"  Type: {contract['contract_type']}")
            print(f"  Status: {contract['status']}")
            print(f"  Value: {contract['value']} {contract['currency']}")
    else:
        print(f"Error: {response.text}")

def test_contract_detail(contract_id):
    """Test the contract detail endpoint"""
    print(f"Testing contract detail endpoint for contract {contract_id}...")
    response = requests.get(f"{BASE_URL}/contracts/{contract_id}")
    print(f"Status code: {response.status_code}")
    
    if response.status_code == 200:
        contract = response.json()
        print(f"Contract details:")
        print(f"  Title: {contract['title']}")
        print(f"  Type: {contract['contract_type']}")
        print(f"  Status: {contract['status']}")
        print(f"  Value: {contract['value']} {contract['currency']}")
        print(f"  Start date: {contract['start_date']}")
        print(f"  End date: {contract['end_date']}")
        
        if 'parties' in contract and contract['parties']:
            print("\nParties:")
            for party in contract['parties']:
                print(f"  {party['party_type'].capitalize()}: {party['legal_name']}")
                print(f"  Contact: {party['contact_person']}")
                print(f"  Email: {party['email']}")
        
        if 'metadata' in contract and contract['metadata']:
            print("\nMetadata:")
            metadata = contract['metadata']
            print(f"  Jurisdiction: {metadata.get('jurisdiction', 'N/A')}")
            print(f"  Governing law: {metadata.get('governing_law', 'N/A')}")
            print(f"  AI confidence score: {metadata.get('ai_confidence_score', 'N/A')}")
    else:
        print(f"Error: {response.text}")

def test_contract_metrics():
    """Test the contract metrics endpoint"""
    print("Testing contract metrics endpoint...")
    response = requests.get(f"{BASE_URL}/contracts/metrics")
    print(f"Status code: {response.status_code}")
    
    if response.status_code == 200:
        metrics = response.json()
        print("Contract metrics:")
        print(f"  Total contracts: {metrics['total_contracts']}")
        print(f"  Active contracts: {metrics['active_contracts']}")
        print(f"  Expiring soon: {metrics['expiring_soon']}")
        print(f"  Renewal rate: {metrics['renewal_rate']}%")
        print(f"  Total value: {metrics['total_value']}")
        
        print("\nContracts by type:")
        for contract_type, count in metrics['contracts_by_type'].items():
            print(f"  {contract_type}: {count}")
        
        print("\nContracts by status:")
        for status, count in metrics['contracts_by_status'].items():
            print(f"  {status}: {count}")
    else:
        print(f"Error: {response.text}")

def test_create_contract():
    """Test creating a new contract"""
    print("Testing contract creation...")
    
    # Mock contract data
    data = {
        "title": f"Test Contract {datetime.now().strftime('%Y%m%d%H%M%S')}",
        "contract_type": "SERVICE_AGREEMENT",
        "description": "This is a test contract created via API",
        "start_date": datetime.now().isoformat(),
        "end_date": (datetime.now() + timedelta(days=365)).isoformat(),
        "value": 50000,
        "currency": "USD",
        "payment_terms": "Net 30",
        "tags": "test,api,automated",
        "party_name": "Test Client Ltd.",
        "party_type": "client",
        "party_address": "123 Test Street, Test City",
        "party_contact": "John Doe",
        "party_email": "john@testclient.com",
        "party_phone": "555-123-4567"
    }
    
    # Simulate a file upload without an actual file
    files = {}
    
    response = requests.post(f"{BASE_URL}/contracts", data=data, files=files)
    print(f"Status code: {response.status_code}")
    
    if response.status_code == 201:
        contract = response.json()
        print("Contract created successfully!")
        print(f"  ID: {contract['id']}")
        print(f"  Contract number: {contract['contract_number']}")
        print(f"  Title: {contract['title']}")
        return contract['id']
    else:
        print(f"Error: {response.text}")
        return None

def test_ai_endpoints():
    """Test AI endpoints"""
    print("Testing AI endpoints...")
    print("\nNote: Full AI endpoint testing requires file uploads.")
    print("Using simple text-only examples instead.")
    
    # Test analyze-risk endpoint
    print("\nTesting analyze-risk endpoint...")
    risk_data = {
        "contract_data": {
            "title": "High Risk Service Agreement",
            "contract_type": "SERVICE_AGREEMENT",
            "value": 2000000,
            "currency": "USD",
            "termination_clause": "No early termination allowed.",
            "limitation_of_liability": "Liability is unlimited for all parties.",
            "governing_law": "Unspecified"
        }
    }
    
    response = requests.post(f"{BASE_URL}/ai/analyze-risk", json=risk_data)
    print(f"Status code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("Risk analysis result:")
        print(f"  Success: {result['success']}")
        print(f"  Risk assessment:")
        assessment = result['risk_assessment']
        print(f"    Risk score: {assessment.get('risk_score', 'N/A')}")
        print(f"    Risk level: {assessment.get('risk_level', 'N/A')}")
        print("\n    Risk factors:")
        for factor in assessment.get('risk_factors', []):
            print(f"      - {factor}")
    else:
        print(f"Error: {response.text}")
    
    # Test analyze-clauses endpoint
    print("\nTesting analyze-clauses endpoint...")
    clauses_data = {
        "clauses": {
            "termination_clause": "Either party may terminate this agreement with 30 days written notice.",
            "confidentiality_clause": "All information shared shall be kept confidential for a period of 5 years.",
            "payment_terms": "Payment due within 30 days of invoice date."
            # Intentionally missing important clauses
        }
    }
    
    response = requests.post(f"{BASE_URL}/ai/analyze-clauses", json=clauses_data)
    print(f"Status code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("Clause analysis result:")
        print(f"  Success: {result['success']}")
        analysis = result['analysis']
        print(f"  Analysis summary: {analysis.get('analysis', 'N/A')[:100]}...")
        print("\n  Missing clauses:")
        for clause in analysis.get('missing_clauses', []):
            print(f"    - {clause}")
    else:
        print(f"Error: {response.text}")

def main():
    """Main function to handle script arguments"""
    parser = argparse.ArgumentParser(description="API testing script")
    parser.add_argument("endpoint", nargs="?", default="health",
                       choices=["health", "contracts", "contract", "metrics", 
                                "create", "ai", "all"],
                       help="Endpoint to test")
    parser.add_argument("--id", type=int, help="Contract ID for detailed view")
    
    args = parser.parse_args()
    
    if args.endpoint == "health":
        test_health()
    elif args.endpoint == "contracts":
        test_contracts_list()
    elif args.endpoint == "contract":
        if not args.id:
            print("Error: Contract ID is required for contract detail endpoint")
            print("Usage: python api_test.py contract --id=1")
            sys.exit(1)
        test_contract_detail(args.id)
    elif args.endpoint == "metrics":
        test_contract_metrics()
    elif args.endpoint == "create":
        test_create_contract()
    elif args.endpoint == "ai":
        test_ai_endpoints()
    elif args.endpoint == "all":
        test_health()
        print("\n" + "="*50 + "\n")
        test_contracts_list()
        print("\n" + "="*50 + "\n")
        test_contract_metrics()
        print("\n" + "="*50 + "\n")
        contract_id = test_create_contract()
        if contract_id:
            print("\n" + "="*50 + "\n")
            test_contract_detail(contract_id)
        print("\n" + "="*50 + "\n")
        test_ai_endpoints()

if __name__ == "__main__":
    main()