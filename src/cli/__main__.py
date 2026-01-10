"""
CLI entry point for medical GraphRAG management.
Usage: python -m src.cli check-health
"""

import sys
import argparse
import json
import time
from typing import List, Optional, Dict
from src.validation.health_checks import run_all_checks, HealthCheckResult
from src.search.hybrid_search import HybridSearchService
from src.setup.create_text_vector_table import create_text_vector_table
from src.cli.chat import run_chat_cli

def format_report(results: List[HealthCheckResult], duration: float, smoke_test: Optional[Dict] = None) -> str:
    """Format health check results as JSON."""
    all_passed = all(r.status == "pass" for r in results)
    if smoke_test and smoke_test.get("status") == "fail":
        all_passed = False
    
    report = {
        "status": "pass" if all_passed else "fail",
        "duration_ms": int(duration * 1000),
        "checks": [r.to_dict() for r in results]
    }
    if smoke_test:
        report["smoke_test"] = smoke_test
    return json.dumps(report, indent=2)

def check_health_command(args):
    """Execute the check-health command."""
    start_time = time.time()
    
    smoke_test_result = None
    if args.smoke_test:
        try:
            service = HybridSearchService()
            search_results = service.search("fever", top_k=1)
            smoke_test_result = {
                "status": "pass",
                "results_count": search_results.get("results_count", 0),
                "top_result_id": search_results["top_documents"][0]["fhir_id"] if search_results["top_documents"] else None
            }
            service.close()
        except Exception as e:
            smoke_test_result = {
                "status": "fail",
                "error": str(e)
            }

    try:
        results = run_all_checks()
        duration = time.time() - start_time
        
        print(format_report(results, duration, smoke_test_result))
        
        all_passed = all(r.status == "pass" for r in results)
        if smoke_test_result and smoke_test_result["status"] == "fail":
            all_passed = False
            
        sys.exit(0 if all_passed else 1)
        
    except Exception as e:
        error_report = {
            "status": "fail",
            "message": f"Critical error during health check: {str(e)}",
            "suggestion": "Check AWS SSO session (aws sso login) or IRIS connectivity"
        }
        print(json.dumps(error_report, indent=2))
        sys.exit(1)

def fix_environment_command(args):
    """Execute the fix-environment command."""
    print("Fixing environment...")
    try:
        print("Ensuring database tables exist...")
        create_text_vector_table()
        print("✅ Environment fix complete")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Failed to fix environment: {e}")
        sys.exit(1)

def chat_command(args):
    import asyncio
    try:
        asyncio.run(run_chat_cli(args.query, provider=args.provider, verbose=not args.quiet))
    except Exception as e:
        print(f"❌ Chat error: {e}")
        sys.exit(1)

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Medical GraphRAG CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # check-health
    health_parser = subparsers.add_parser("check-health", help="Verify system health and schema")
    health_parser.add_argument("--smoke-test", action="store_true", help="Perform a minimal end-to-end search test")
    
    subparsers.add_parser("fix-environment", help="Attempt to fix environment issues (missing tables, etc.)")
    
    chat_parser = subparsers.add_parser("chat", help="Perform an agentic query via terminal")
    chat_parser.add_argument("query", help="Query to perform")
    chat_parser.add_argument("--provider", choices=["nim", "openai", "bedrock"], default="nim", help="LLM provider")
    chat_parser.add_argument("--quiet", action="store_true", help="Hide tool traces")
    
    args = parser.parse_args()
    
    if args.command == "check-health":
        check_health_command(args)
    elif args.command == "fix-environment":
        fix_environment_command(args)
    elif args.command == "chat":
        chat_command(args)
    else:

        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
