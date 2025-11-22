# AWS Deployment Status

**Date**: 2025-11-09
**Status**: 🎉 Community IRIS Fully Operational ✅✅✅
**Python Connectivity**: Working (local + remote) ✅

---

## Deployment Summary

### ✅ Infrastructure Complete
- **EC2 Instance**: i-012abe9cf48fdc702
- **Instance Type**: m5.xlarge
- **Public IP**: 54.172.173.131
- **Region**: us-east-1
- **Security Group**: sg-019518c1317d9af97

### ✅ IRIS Container Running
- **Container**: iris-fhir
- **Image**: intersystemsdc/iris-community:latest (IRIS 2025.1 Build 223U)
- **Status**: Healthy
- **Namespace**: DEMO
- **Ports**:
  - 1972 (SuperServer)
  - 52773 (Management Portal)

### ✅ Connectivity - FULLY WORKING!
- **Management Portal**: ✅ http://54.172.173.131:52773/csp/sys/UtilHome.csp
- **Python iris Driver (EC2)**: ✅ Working
- **Python iris Driver (Local → AWS)**: ✅ Working
- **Credentials**: _SYSTEM / ISCDEMO
- **Test Results**:
  - ✅ Connected from EC2 instance
  - ✅ Connected from local machine to AWS
  - ✅ Queries executing successfully
  - ✅ 452 tables available

---

## Deployment Steps Completed

1. ✅ Created AWS deployment files
   - `docker-compose.aws.yml`
   - `scripts/aws/launch-fhir-stack.sh`

2. ✅ Fixed launch script for IPv4/IPv6 handling
   - Detects IPv4 vs IPv6 automatically
   - Creates appropriate security group rules

3. ✅ Launched EC2 instance
   - Security group created with IP-restricted access
   - 100 GB EBS gp3 volume attached
   - Ubuntu 24.04 LTS

4. ✅ Installed Docker stack
   - Docker 28.5.2
   - Docker Compose v2.40.3

5. ✅ Started IRIS container
   - DEMO namespace created
   - Databases mounted successfully
   - Health check passing

6. ✅ Configured IRIS with iris-devtester + manual fix
   - Installed iris-devtester via pip on EC2
   - `reset_password()` worked but didn't actually set password (bug filed!)
   - Manual ObjectScript fix: `Set prop("Password")="ISCDEMO"`
   - CallIn service enabled successfully
   - **Result**: Python iris driver fully working!

---

## Access Information

### Management Portal
```bash
URL: http://54.172.173.131:52773/csp/sys/UtilHome.csp
Username: _SYSTEM
Password: ISCDEMO
```

### SSH Access
```bash
ssh -i fhir-ai-key.pem ubuntu@54.172.173.131
cd ~/fhir-ai-hackathon
```

### Docker Commands (on EC2)
```bash
# Check status
docker ps

# View logs
docker logs iris-fhir

# Restart container
docker-compose -f docker-compose.aws.yml restart iris-fhir

# Stop stack
docker-compose -f docker-compose.aws.yml down

# Start stack
docker-compose -f docker-compose.aws.yml up -d
```

---

## Cost Management

### Current Costs
- **m5.xlarge**: $0.192/hour = $4.61/day
- **EBS gp3 (100 GB)**: ~$0.27/day
- **Total**: ~$4.88/day running 24/7

### Cost Savings
**Auto-Stop Strategy** (8hrs/day, 20 days/month):
- **Running hours**: 160 hours
- **Cost**: ~$31/month (vs $146/month 24/7)
- **Savings**: 78% ($115/month)

### Stop/Start Commands
```bash
# Stop instance (save costs)
aws ec2 stop-instances --instance-ids i-012abe9cf48fdc702

# Start instance
aws ec2 start-instances --instance-ids i-012abe9cf48fdc702

# Get current IP after restart
aws ec2 describe-instances --instance-ids i-012abe9cf48fdc702 \
  --query 'Reservations[0].Instances[0].PublicIpAddress' --output text
```

---

## Security Group Rules

**sg-019518c1317d9af97**

| Protocol | Port | Source | Purpose |
|----------|------|--------|---------|
| TCP | 22 | Your IPv4/IPv6 | SSH |
| TCP | 1972 | Your IPv4/IPv6 | IRIS SuperServer |
| TCP | 52773 | Your IPv4/IPv6 | Management Portal |

**Security Note**: All ports restricted to your IP address only.

---

## Next Steps

### ✅ READY NOW - Python Connectivity Working!
1. ✅ Run vectorization scripts on AWS
2. ✅ Migrate local IRIS data to AWS (50K+ text vectors, 944 images)
3. ✅ Test vector search queries from local machine
4. ✅ Deploy FHIR server on AWS (optional)

### Production Enhancements
1. Upgrade to licensed IRIS for ACORN=1 (10-50x faster vector search)
2. Add NIM embeddings service (requires g5.xlarge GPU instance)
3. Set up automated backups to S3
4. Configure CloudWatch monitoring
5. Implement auto-stop/start scripts for cost savings

---

## Files Created

**Deployment Scripts**:
- `docker-compose.aws.yml` - Docker Compose for EC2
- `scripts/aws/launch-fhir-stack.sh` - Automated EC2 launch
- `fhir-ai-key.pem` - SSH key pair

**Documentation**:
- `AWS_DEPLOYMENT_PLAN.md` - Comprehensive deployment guide
- `AWS_DEPLOYMENT_STATUS.md` - This file

---

## Troubleshooting

### Issue: SSH Connection Timeout ✅ FIXED
**Cause**: Security group missing IPv4 rules (script only added IPv6)
**Fix**: Updated launch script to detect IPv4 vs IPv6 and add appropriate rules

### Issue: Python iris Driver "Access Denied" ✅ FIXED
**Cause**: iris-devtester's `reset_password()` doesn't actually SET the password
**Root Issue**: Function only unexpires password, doesn't set `prop("Password")="ISCDEMO"`

**Solution** (on EC2):
```bash
# SSH into EC2
ssh -i fhir-ai-key.pem ubuntu@54.172.173.131

# Set password manually via ObjectScript
docker exec iris-fhir bash -c 'echo -e "Set sc = ##class(Security.Users).Get(\"_SYSTEM\",.prop)\nSet prop(\"Password\")=\"ISCDEMO\"\nSet prop(\"PasswordNeverExpires\")=1\nSet sc = ##class(Security.Users).Modify(\"_SYSTEM\",.prop)\nHalt" | iris session IRIS -U %SYS'
```

**Bug Filed**: See `IRIS_DEVTESTER_FEEDBACK.md` - Issue #9: "reset_password() Doesn't Actually Set the Password!"

### Issue: Instance IP Changes After Restart
**Solution**: Get new IP after each restart:
```bash
aws ec2 describe-instances --instance-ids i-012abe9cf48fdc702 \
  --query 'Reservations[0].Instances[0].PublicIpAddress' --output text
```

---

## Summary

**AWS deployment successful!**

IRIS is running on EC2 with community edition, Management Portal accessible, and ready for manual operations. Python connectivity pending iris-devtester team's docker-compose improvements.

**Cost**: ~$31/month with smart 8hrs/day usage
**Performance**: Suitable for development and demos
**Upgrade Path**: Licensed IRIS ready when needed
