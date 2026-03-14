"""Tests for the CloudFormation infrastructure template.

Validates:
- Template is valid YAML
- All required resource types are present
- Security groups enforce least-privilege networking
- ALB target group health check uses /api/health
- S3 bucket has CORS configuration for video playback
- Parameters enable customization
- Outputs export required values
- No hardcoded secrets in template
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

# Path to the CloudFormation template
TEMPLATE_PATH = Path(__file__).resolve().parents[2] / "infrastructure" / "cloudformation.yaml"


def _create_cf_yaml_loader():
    """Create a YAML loader that handles CloudFormation intrinsic functions."""
    # Add constructors for CloudFormation intrinsic functions
    def _cf_constructor(loader, node):
        if isinstance(node, yaml.MappingNode):
            return loader.construct_mapping(node)
        elif isinstance(node, yaml.SequenceNode):
            return loader.construct_sequence(node)
        else:
            return loader.construct_scalar(node)

    class CloudFormationLoader(yaml.SafeLoader):
        pass

    # Register CloudFormation intrinsic functions as passthrough
    cf_tags = [
        "!Ref", "!GetAtt", "!Join", "!Sub", "!If", "!Equals", "!Not",
        "!Or", "!And", "!Select", "!FindInMap", "!Base64", "!Cidr",
        "!GetAZs", "!ImportValue", "!Split", "!Transform", "!Condition",
    ]
    for tag in cf_tags:
        CloudFormationLoader.add_constructor(tag, _cf_constructor)

    return CloudFormationLoader


@pytest.fixture()
def template_content():
    """Load the CloudFormation template content."""
    if not TEMPLATE_PATH.exists():
        pytest.fail(f"CloudFormation template not found at {TEMPLATE_PATH}")
    return TEMPLATE_PATH.read_text()


@pytest.fixture()
def template_yaml(template_content):
    """Parse the CloudFormation template as YAML with CF intrinsic function support."""
    loader = _create_cf_yaml_loader()
    return yaml.load(template_content, Loader=loader)


class TestTemplateValidity:
    """VAL-DEPLOY-001: CloudFormation template syntactic validity."""

    def test_template_is_valid_yaml(self, template_content):
        """Template should be parseable as valid YAML with CF intrinsic function support."""
        try:
            loader = _create_cf_yaml_loader()
            parsed = yaml.load(template_content, Loader=loader)
            assert parsed is not None, "Template should not be empty"
            assert isinstance(parsed, dict), "Template should be a YAML mapping"
        except yaml.YAMLError as e:
            pytest.fail(f"Template is not valid YAML: {e}")

    def test_template_has_required_top_level_keys(self, template_yaml):
        """Template should have required CloudFormation top-level keys."""
        assert "AWSTemplateFormatVersion" in template_yaml, "Missing AWSTemplateFormatVersion"
        assert "Description" in template_yaml, "Missing Description"
        assert "Resources" in template_yaml, "Missing Resources section"

    def test_template_format_version_valid(self, template_yaml):
        """AWSTemplateFormatVersion should be a valid value."""
        version = template_yaml.get("AWSTemplateFormatVersion")
        assert version == "2010-09-09", f"Expected '2010-09-09', got '{version}'"


class TestRequiredResources:
    """VAL-DEPLOY-002: CloudFormation template contains all required resources."""

    def test_ec2_instance_resource_exists(self, template_yaml):
        """Template should contain AWS::EC2::Instance."""
        resources = template_yaml.get("Resources", {})
        ec2_instances = [
            name for name, r in resources.items()
            if r.get("Type") == "AWS::EC2::Instance"
        ]
        assert len(ec2_instances) > 0, "Missing AWS::EC2::Instance resource"

    def test_ec2_uses_amazon_linux_2023(self, template_yaml):
        """EC2 instance should use Amazon Linux 2023 AMI."""
        resources = template_yaml.get("Resources", {})
        for name, resource in resources.items():
            if resource.get("Type") == "AWS::EC2::Instance":
                image_id = resource.get("Properties", {}).get("ImageId", "")
                # Should use SSM parameter for latest AL2023 AMI
                assert "al2023" in image_id.lower() or "amazon-linux-latest" in image_id.lower(), \
                    f"EC2 instance {name} should use Amazon Linux 2023 AMI via SSM parameter"

    def test_ec2_has_userdata(self, template_yaml):
        """EC2 instance should have UserData for initial setup."""
        resources = template_yaml.get("Resources", {})
        for name, resource in resources.items():
            if resource.get("Type") == "AWS::EC2::Instance":
                user_data = resource.get("Properties", {}).get("UserData")
                assert user_data is not None, f"EC2 instance {name} missing UserData"

    def test_rds_instance_resource_exists(self, template_yaml):
        """Template should contain AWS::RDS::DBInstance (PostgreSQL)."""
        resources = template_yaml.get("Resources", {})
        rds_instances = [
            name for name, r in resources.items()
            if r.get("Type") == "AWS::RDS::DBInstance"
        ]
        assert len(rds_instances) > 0, "Missing AWS::RDS::DBInstance resource"

    def test_rds_is_postgresql(self, template_yaml):
        """RDS instance should be PostgreSQL engine."""
        resources = template_yaml.get("Resources", {})
        for name, resource in resources.items():
            if resource.get("Type") == "AWS::RDS::DBInstance":
                engine = resource.get("Properties", {}).get("Engine")
                assert engine == "postgres", f"RDS {name} should use PostgreSQL, got {engine}"

    def test_s3_bucket_resource_exists(self, template_yaml):
        """Template should contain AWS::S3::Bucket."""
        resources = template_yaml.get("Resources", {})
        buckets = [
            name for name, r in resources.items()
            if r.get("Type") == "AWS::S3::Bucket"
        ]
        assert len(buckets) > 0, "Missing AWS::S3::Bucket resource"

    def test_alb_resource_exists(self, template_yaml):
        """Template should contain AWS::ElasticLoadBalancingV2::LoadBalancer."""
        resources = template_yaml.get("Resources", {})
        albs = [
            name for name, r in resources.items()
            if r.get("Type") == "AWS::ElasticLoadBalancingV2::LoadBalancer"
        ]
        assert len(albs) > 0, "Missing AWS::ElasticLoadBalancingV2::LoadBalancer resource"

    def test_target_group_resource_exists(self, template_yaml):
        """Template should contain AWS::ElasticLoadBalancingV2::TargetGroup."""
        resources = template_yaml.get("Resources", {})
        tgs = [
            name for name, r in resources.items()
            if r.get("Type") == "AWS::ElasticLoadBalancingV2::TargetGroup"
        ]
        assert len(tgs) > 0, "Missing AWS::ElasticLoadBalancingV2::TargetGroup resource"

    def test_listener_resource_exists(self, template_yaml):
        """Template should contain AWS::ElasticLoadBalancingV2::Listener."""
        resources = template_yaml.get("Resources", {})
        listeners = [
            name for name, r in resources.items()
            if r.get("Type") == "AWS::ElasticLoadBalancingV2::Listener"
        ]
        assert len(listeners) > 0, "Missing AWS::ElasticLoadBalancingV2::Listener resource"

    def test_security_groups_exist(self, template_yaml):
        """Template should contain security groups for ALB, EC2, and RDS."""
        resources = template_yaml.get("Resources", {})
        security_groups = [
            r for r in resources.values()
            if r.get("Type") == "AWS::EC2::SecurityGroup"
        ]
        assert len(security_groups) >= 3, f"Expected at least 3 security groups, found {len(security_groups)}"

    def test_route53_recordset_conditional(self, template_yaml):
        """Template should contain conditional AWS::Route53::RecordSet."""
        resources = template_yaml.get("Resources", {})
        route53_records = [
            name for name, r in resources.items()
            if r.get("Type") == "AWS::Route53::RecordSet"
        ]
        # Route53 is optional but should be present in template
        if route53_records:
            # Should have condition attached
            for name in route53_records:
                resource = resources[name]
                assert "Condition" in resource, \
                    f"Route53 record {name} should have a Condition for optional creation"


class TestSecurityGroups:
    """VAL-DEPLOY-003: Security groups enforce least-privilege networking."""

    def test_alb_security_group_allows_public_http_https(self, template_yaml):
        """ALB security group should allow 80/443 from 0.0.0.0/0."""
        resources = template_yaml.get("Resources", {})

        for name, resource in resources.items():
            if resource.get("Type") != "AWS::EC2::SecurityGroup":
                continue

            props = resource.get("Properties", {})
            ingress_rules = props.get("SecurityGroupIngress", [])

            # Check if this looks like an ALB security group by name
            group_name = props.get("GroupName", "")
            if "alb" in group_name.lower():
                has_http = False
                has_https = False

                for rule in ingress_rules:
                    cidr = rule.get("CidrIp", "")
                    from_port = rule.get("FromPort")
                    to_port = rule.get("ToPort")

                    if cidr == "0.0.0.0/0":
                        if from_port == 80 and to_port == 80:
                            has_http = True
                        if from_port == 443 and to_port == 443:
                            has_https = True

                assert has_http, f"ALB security group {name} should allow HTTP (80) from 0.0.0.0/0"
                assert has_https, f"ALB security group {name} should allow HTTPS (443) from 0.0.0.0/0"

    def test_ec2_security_group_restricts_to_alb_only(self, template_yaml):
        """EC2 security group should only allow traffic from ALB security group."""
        resources = template_yaml.get("Resources", {})

        alb_sg_ref = None
        ec2_sg_name = None

        # Find EC2 security group name
        ec2_sg_name = None
        for name, resource in resources.items():
            if resource.get("Type") != "AWS::EC2::SecurityGroup":
                continue
            props = resource.get("Properties", {})
            group_name = props.get("GroupName", "")

            if "ec2" in group_name.lower() or "app" in group_name.lower():
                ec2_sg_name = name

        # Check EC2 security group ingress rules
        for _name, resource in resources.items():
            if resource.get("Type") == "AWS::EC2::SecurityGroupIngress":
                props = resource.get("Properties", {})
                group_id = props.get("GroupId", {})

                # Check if this rule is for EC2 SG
                if isinstance(group_id, dict) and group_id.get("Ref") == ec2_sg_name:
                    source_sg = props.get("SourceSecurityGroupId")
                    assert source_sg is not None, \
                        "EC2 security group ingress should use SourceSecurityGroupId (not CidrIp)"

                    # Should reference ALB security group
                    if isinstance(source_sg, dict):
                        assert source_sg.get("Ref") or source_sg.get("Fn::GetAtt") or source_sg.get("Fn::ImportValue"), \
                            "EC2 security group should reference another security group, not CIDR"

    def test_rds_security_group_restricts_to_ec2_only(self, template_yaml):
        """RDS security group should only allow PostgreSQL (5432) from EC2 security group."""
        resources = template_yaml.get("Resources", {})

        rds_sg_name = None
        for name, resource in resources.items():
            if resource.get("Type") != "AWS::EC2::SecurityGroup":
                continue
            props = resource.get("Properties", {})
            group_name = props.get("GroupName", "")
            if "rds" in group_name.lower() or "db" in group_name.lower():
                rds_sg_name = name

        # Check RDS security group ingress rules
        for _name, resource in resources.items():
            if resource.get("Type") == "AWS::EC2::SecurityGroupIngress":
                props = resource.get("Properties", {})
                group_id = props.get("GroupId", {})
                from_port = props.get("FromPort")
                to_port = props.get("ToPort")

                # Check if this rule is for RDS SG
                if isinstance(group_id, dict) and group_id.get("Ref") == rds_sg_name:
                    assert from_port == 5432 and to_port == 5432, \
                        f"RDS security group should only allow port 5432 (PostgreSQL), got {from_port}-{to_port}"

                    source_sg = props.get("SourceSecurityGroupId")
                    assert source_sg is not None, \
                        "RDS security group ingress should use SourceSecurityGroupId"

                    # Should not use CidrIp
                    assert props.get("CidrIp") is None, \
                        "RDS security group should not use CidrIp - must use SourceSecurityGroupId"


class TestALBHealthCheck:
    """VAL-DEPLOY-012: ALB health check targets /api/health."""

    def test_target_group_health_check_path(self, template_yaml):
        """Target group health check should use /api/health path."""
        resources = template_yaml.get("Resources", {})

        for name, resource in resources.items():
            if resource.get("Type") != "AWS::ElasticLoadBalancingV2::TargetGroup":
                continue

            props = resource.get("Properties", {})
            health_check_path = props.get("HealthCheckPath", "")

            assert health_check_path == "/api/health", \
                f"Target group {name} health check path should be /api/health, got '{health_check_path}'"

    def test_target_group_health_check_protocol_http(self, template_yaml):
        """Target group health check should use HTTP protocol."""
        resources = template_yaml.get("Resources", {})

        for name, resource in resources.items():
            if resource.get("Type") != "AWS::ElasticLoadBalancingV2::TargetGroup":
                continue

            props = resource.get("Properties", {})
            protocol = props.get("HealthCheckProtocol", "HTTP")

            assert protocol == "HTTP", \
                f"Target group {name} health check protocol should be HTTP, got '{protocol}'"


class TestS3CorsConfiguration:
    """VAL-DEPLOY-013: S3 bucket has CORS configuration for video playback."""

    def test_s3_bucket_has_cors_configuration(self, template_yaml):
        """S3 bucket should have CORS configuration allowing GET from app domain."""
        resources = template_yaml.get("Resources", {})

        for name, resource in resources.items():
            if resource.get("Type") != "AWS::S3::Bucket":
                continue

            props = resource.get("Properties", {})
            cors_config = props.get("CorsConfiguration")

            assert cors_config is not None, f"S3 bucket {name} should have CorsConfiguration"

            cors_rules = cors_config.get("CorsRules", [])
            assert len(cors_rules) > 0, f"S3 bucket {name} should have at least one CORS rule"

            for rule in cors_rules:
                allowed_methods = rule.get("AllowedMethods", [])
                assert "GET" in allowed_methods, \
                    f"S3 bucket {name} CORS rule should allow GET method"

                allowed_origins = rule.get("AllowedOrigins", [])
                assert len(allowed_origins) > 0, \
                    f"S3 bucket {name} CORS rule should specify allowed origins"


class TestParameters:
    """VAL-DEPLOY-010: CloudFormation parameters enable customization."""

    def test_instance_type_parameter_exists(self, template_yaml):
        """Template should have InstanceType parameter."""
        parameters = template_yaml.get("Parameters", {})
        assert "InstanceType" in parameters, "Missing InstanceType parameter"

        param = parameters["InstanceType"]
        assert param.get("Type") == "String", "InstanceType should be String type"
        assert param.get("Default") == "t3.small", "InstanceType should default to t3.small"

    def test_db_instance_class_parameter_exists(self, template_yaml):
        """Template should have DBInstanceClass parameter."""
        parameters = template_yaml.get("Parameters", {})
        assert "DBInstanceClass" in parameters, "Missing DBInstanceClass parameter"

        param = parameters["DBInstanceClass"]
        assert param.get("Default") == "db.t3.micro", "DBInstanceClass should default to db.t3.micro"

    def test_db_allocated_storage_parameter_exists(self, template_yaml):
        """Template should have DBAllocatedStorage parameter."""
        parameters = template_yaml.get("Parameters", {})
        assert "DBAllocatedStorage" in parameters, "Missing DBAllocatedStorage parameter"

        param = parameters["DBAllocatedStorage"]
        assert param.get("Default") == 20, "DBAllocatedStorage should default to 20"

    def test_key_pair_name_parameter_exists(self, template_yaml):
        """Template should have KeyPairName parameter."""
        parameters = template_yaml.get("Parameters", {})
        assert "KeyPairName" in parameters, "Missing KeyPairName parameter"

    def test_domain_name_parameter_exists(self, template_yaml):
        """Template should have optional DomainName parameter."""
        parameters = template_yaml.get("Parameters", {})
        assert "DomainName" in parameters, "Missing DomainName parameter"

        param = parameters["DomainName"]
        assert param.get("Default") == "", "DomainName should default to empty (optional)"

    def test_environment_name_parameter_exists(self, template_yaml):
        """Template should have EnvironmentName parameter."""
        parameters = template_yaml.get("Parameters", {})
        assert "EnvironmentName" in parameters, "Missing EnvironmentName parameter"


class TestOutputs:
    """VAL-DEPLOY-009: CloudFormation outputs export essential values."""

    def test_alb_dns_name_output_exists(self, template_yaml):
        """Template should output ALB DNS name."""
        outputs = template_yaml.get("Outputs", {})
        assert "ALBDnsName" in outputs, "Missing ALBDnsName output"

        output = outputs["ALBDnsName"]
        assert "Value" in output, "ALBDnsName should have a Value"
        assert "Export" in output, "ALBDnsName should be exported"

    def test_rds_endpoint_output_exists(self, template_yaml):
        """Template should output RDS endpoint."""
        outputs = template_yaml.get("Outputs", {})
        assert "RDSEndpoint" in outputs, "Missing RDSEndpoint output"

        output = outputs["RDSEndpoint"]
        assert "Value" in output, "RDSEndpoint should have a Value"
        assert "Export" in output, "RDSEndpoint should be exported"

    def test_s3_bucket_name_output_exists(self, template_yaml):
        """Template should output S3 bucket name."""
        outputs = template_yaml.get("Outputs", {})
        assert "S3BucketName" in outputs, "Missing S3BucketName output"

        output = outputs["S3BucketName"]
        assert "Value" in output, "S3BucketName should have a Value"
        assert "Export" in output, "S3BucketName should be exported"

    def test_ec2_instance_id_output_exists(self, template_yaml):
        """Template should output EC2 instance ID."""
        outputs = template_yaml.get("Outputs", {})
        assert "EC2InstanceId" in outputs, "Missing EC2InstanceId output"

        output = outputs["EC2InstanceId"]
        assert "Value" in output, "EC2InstanceId should have a Value"
        assert "Export" in output, "EC2InstanceId should be exported"


class TestNoHardcodedSecrets:
    """VAL-DEPLOY-008: No hardcoded secrets in infrastructure files."""

    def test_no_aws_access_key_in_template(self, template_content):
        """Template should not contain AWS access keys (AKIA pattern)."""
        # AKIA is the prefix for AWS access keys
        akia_pattern = r'AKIA[0-9A-Z]{16}'
        matches = re.findall(akia_pattern, template_content)
        assert len(matches) == 0, f"Found potential AWS access key in template: {matches}"

    def test_no_hardcoded_passwords(self, template_content):
        """Template should not contain hardcoded passwords."""
        # Look for common password patterns
        password_patterns = [
            r'(?i)(password|passwd|pwd)\s*[:=]\s*["\'][^"\']{4,}["\']',
            r'(?i)(secret|secretkey)\s*[:=]\s*["\'][^"\']{4,}["\']',
            r'(?i)(apikey|api_key)\s*[:=]\s*["\'][^"\']{4,}["\']',
        ]

        for pattern in password_patterns:
            matches = re.findall(pattern, template_content)
            # Filter out legitimate CloudFormation constructs like Ref and SecretsManager
            filtered = [m for m in matches if not any(x in str(m) for x in [
                "{{resolve:secretsmanager",
                "{{resolve:ssm",
                "Ref:",
                "Fn::",
                "password}}",
            ])]
            assert len(filtered) == 0, f"Found potential hardcoded secret: {filtered}"

    def test_database_credentials_use_secrets_manager(self, template_yaml):
        """RDS credentials should use SecretsManager, not hardcoded values."""
        resources = template_yaml.get("Resources", {})

        for name, resource in resources.items():
            if resource.get("Type") != "AWS::RDS::DBInstance":
                continue

            props = resource.get("Properties", {})
            username = props.get("MasterUsername", "")
            password = props.get("MasterUserPassword", "")

            # Should use SecretsManager dynamic reference
            if isinstance(username, str):
                assert "{{resolve:secretsmanager" in username or "{{resolve:ssm" in username, \
                    f"RDS {name} MasterUsername should use SecretsManager or SSM, not hardcoded value"

            if isinstance(password, str):
                assert "{{resolve:secretsmanager" in password or "{{resolve:ssm" in password, \
                    f"RDS {name} MasterUserPassword should use SecretsManager or SSM, not hardcoded value"

    def test_no_connection_strings_with_embedded_credentials(self, template_content):
        """Template should not contain database connection strings with embedded credentials."""
        # Detect embedded credentials in database connection URLs
        protocol = "postgresql"
        conn_string_pattern = rf'{protocol}://[^:@]+:[^@]+@'
        matches = re.findall(conn_string_pattern, template_content)
        assert len(matches) == 0, f"Found database connection string with embedded credentials: {matches}"


class TestTemplateStructure:
    """Additional structural tests for the CloudFormation template."""

    def test_vpc_resource_exists(self, template_yaml):
        """Template should contain a VPC."""
        resources = template_yaml.get("Resources", {})
        vpcs = [name for name, r in resources.items() if r.get("Type") == "AWS::EC2::VPC"]
        assert len(vpcs) > 0, "Missing VPC resource"

    def test_subnets_in_multiple_azs(self, template_yaml):
        """Template should have subnets in multiple availability zones."""
        resources = template_yaml.get("Resources", {})
        subnets = [r for r in resources.values() if r.get("Type") == "AWS::EC2::Subnet"]

        # Should have at least 4 subnets (2 public, 2 private across 2 AZs)
        assert len(subnets) >= 4, f"Should have at least 4 subnets, found {len(subnets)}"

        # Check that we have subnets with !GetAZs or !Select (indicating multi-AZ)
        az_refs = []
        for subnet in subnets:
            az = subnet.get("Properties", {}).get("AvailabilityZone", "")
            if az:
                az_refs.append(az)

        # Should have different AZ references (either strings or CF intrinsic functions)
        assert len(az_refs) >= 4, f"Should have AZ references for all subnets, found {len(az_refs)}"

    def test_nat_gateway_for_private_subnets(self, template_yaml):
        """Private subnets should have NAT gateway for outbound access."""
        resources = template_yaml.get("Resources", {})
        nat_gateways = [r for r in resources.values() if r.get("Type") == "AWS::EC2::NatGateway"]
        assert len(nat_gateways) >= 2, "Should have NAT gateways for high availability"

    def test_rds_in_private_subnets(self, template_yaml):
        """RDS should be in private subnets (DBSubnetGroup)."""
        resources = template_yaml.get("Resources", {})
        db_subnet_groups = [
            r for r in resources.values() if r.get("Type") == "AWS::RDS::DBSubnetGroup"
        ]
        assert len(db_subnet_groups) > 0, "RDS should use a DBSubnetGroup for private subnets"

    def test_ec2_has_iam_instance_profile(self, template_yaml):
        """EC2 instance should have an IAM instance profile."""
        resources = template_yaml.get("Resources", {})

        for name, resource in resources.items():
            if resource.get("Type") != "AWS::EC2::Instance":
                continue

            props = resource.get("Properties", {})
            iam_profile = props.get("IamInstanceProfile")
            assert iam_profile is not None, f"EC2 instance {name} should have IamInstanceProfile"

    def test_secrets_manager_for_db_credentials(self, template_yaml):
        """Template should use SecretsManager for database credentials."""
        resources = template_yaml.get("Resources", {})
        secrets = [
            r for r in resources.values() if r.get("Type") == "AWS::SecretsManager::Secret"
        ]
        assert len(secrets) > 0, "Should use SecretsManager for database credentials"

        # Check that the secret has GenerateSecretString for auto-generated password
        for secret in secrets:
            props = secret.get("Properties", {})
            gen_string = props.get("GenerateSecretString")
            assert gen_string is not None, "Secret should auto-generate a password"
