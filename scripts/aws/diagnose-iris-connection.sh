#!/usr/bin/env bash
#
# IRIS Connection Diagnostic Script
# Diagnoses connectivity and authentication issues with AWS IRIS instance
#

set -euo pipefail

# Colors
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

AWS_HOST="3.84.250.46"
IRIS_PORT_SQL=1972
IRIS_PORT_WEB=52773
CONTAINER_NAME="iris-vector-db"

echo "======================================================================"
echo "IRIS Connection Diagnostics"
echo "======================================================================"

# Test 1: Network connectivity
echo -e "\n${BLUE}→${NC} Test 1: Network Connectivity"
if nc -zv -w5 "$AWS_HOST" "$IRIS_PORT_SQL" 2>&1 | grep -q "succeeded"; then
    echo -e "${GREEN}✓${NC} SQL port $IRIS_PORT_SQL is reachable"
else
    echo -e "${RED}✗${NC} SQL port $IRIS_PORT_SQL is NOT reachable"
    exit 1
fi

if curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "http://$AWS_HOST:$IRIS_PORT_WEB/csp/sys/UtilHome.csp" | grep -q "200"; then
    echo -e "${GREEN}✓${NC} Management Portal port $IRIS_PORT_WEB is accessible"
else
    echo -e "${RED}✗${NC} Management Portal is NOT accessible"
fi

# Test 2: Container Status (requires SSH)
echo -e "\n${BLUE}→${NC} Test 2: Container Status (requires SSH access)"
echo "Run on AWS instance:"
echo "  ssh ubuntu@$AWS_HOST 'docker ps | grep $CONTAINER_NAME'"
echo "  ssh ubuntu@$AWS_HOST 'docker logs $CONTAINER_NAME --tail 50'"

# Test 3: Python IRIS connection
echo -e "\n${BLUE}→${NC} Test 3: Python Connection Test"
python3 << 'PYEOF'
import sys
try:
    import iris
    print("  ✓ intersystems-irispython is installed")

    # Test connection with different formats
    host = "3.84.250.46"
    port = 1972
    user = "_SYSTEM"
    pwd = "SYS"

    formats = [
        ("Positional (host, port, %SYS, user, pass)",
         lambda: iris.connect(host, port, "%SYS", user, pwd)),
        ("Positional (host, port, DEMO, user, pass)",
         lambda: iris.connect(host, port, "DEMO", user, pwd)),
        ("Connection string (host:port/%SYS)",
         lambda: iris.connect(f"{host}:{port}/%SYS", user, pwd)),
        ("Connection string (host:port/DEMO)",
         lambda: iris.connect(f"{host}:{port}/DEMO", user, pwd)),
    ]

    success_count = 0
    for desc, conn_fn in formats:
        try:
            print(f"\n  Testing: {desc}")
            conn = conn_fn()
            print(f"    ✓ Connected successfully")
            cursor = conn.cursor()
            cursor.execute("SELECT $ZVERSION")
            version = cursor.fetchone()[0]
            print(f"    ✓ IRIS Version: {version[:50]}...")
            conn.close()
            success_count += 1
        except Exception as e:
            error_msg = str(e)
            print(f"    ✗ Failed: {error_msg[:100]}")
            if "Access Denied" in error_msg:
                print("    ⚠ Possible causes:")
                print("      - Password change required")
                print("      - Container restarted with different password")
                print("      - Authentication configuration changed")

    if success_count == 0:
        print("\n  ⚠ All connection formats failed")
        sys.exit(1)
    else:
        print(f"\n  ✓ {success_count}/{len(formats)} connection formats succeeded")

except ImportError:
    print("  ✗ intersystems-irispython not installed")
    print("    Run: pip install intersystems-irispython")
    sys.exit(1)
except Exception as e:
    print(f"  ✗ Unexpected error: {e}")
    sys.exit(1)
PYEOF

if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✓${NC} Python connection test passed"
else
    echo -e "\n${RED}✗${NC} Python connection test failed"
    echo ""
    echo "======================================================================"
    echo "Recommended Actions:"
    echo "======================================================================"
    echo ""
    echo "1. Check IRIS container logs:"
    echo "   ssh ubuntu@$AWS_HOST"
    echo "   docker logs $CONTAINER_NAME --tail 100"
    echo ""
    echo "2. Verify container is running:"
    echo "   docker ps | grep $CONTAINER_NAME"
    echo ""
    echo "3. Check IRIS password status:"
    echo "   docker exec $CONTAINER_NAME iris session IRIS -U%SYS"
    echo "   set sc = ##class(Security.Users).Get(\"_SYSTEM\", .props)"
    echo "   zwrite props"
    echo ""
    echo "4. Reset password if needed:"
    echo "   docker exec $CONTAINER_NAME iris session IRIS << 'EOF'"
    echo "   zn \"%SYS\""
    echo "   set sc = ##class(Security.Users).Get(\"_SYSTEM\", .props)"
    echo "   set props(\"PasswordNeverExpires\") = 1"
    echo "   set sc = ##class(Security.Users).Modify(\"_SYSTEM\", .props)"
    echo "   write \"Password policy updated\""
    echo "   EOF"
    echo ""
    echo "5. Restart IRIS container if needed:"
    echo "   docker restart $CONTAINER_NAME"
    echo ""
    exit 1
fi

echo ""
echo "======================================================================"
echo "✅ All diagnostic tests passed"
echo "======================================================================"
