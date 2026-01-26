import boto3
import questionary
from botocore.exceptions import ClientError, NoCredentialsError
from questionary import Choice


def get_tag_value(tags, key="Name"):
    """Helper to safely extract a tag value from a list of tags."""
    if not tags:
        return None
    for tag in tags:
        if tag["Key"] == key:
            return tag["Value"]
    return None


def select_network_resources(region_name="us-east-1"):
    """
    Interactively select a VPC, 2-3 Subnets, and Security Groups.
    """
    try:
        # Initialize Boto3 EC2 client
        ec2 = boto3.client("ec2", region_name=region_name)

        # ==========================================
        # Step 1: Fetch and Select VPC
        # ==========================================
        print(f"Fetching VPCs from {region_name}...")
        response = ec2.describe_vpcs()
        vpcs = response.get("Vpcs", [])

        if not vpcs:
            print("No VPCs found in this region.")
            return

        vpc_choices = []
        for vpc in vpcs:
            vpc_id = vpc["VpcId"]
            name = get_tag_value(vpc.get("Tags"))
            display_name = f"{name} ({vpc_id})" if name else vpc_id
            vpc_choices.append(Choice(title=display_name, value=vpc_id))

        selected_vpc_id = questionary.select("Select a VPC:", choices=vpc_choices).ask()

        if not selected_vpc_id:
            return

        # ==========================================
        # Step 2: Fetch and Select Subnets (Min 2, Max 3)
        # ==========================================
        print(f"Fetching subnets for {selected_vpc_id}...")
        response = ec2.describe_subnets(
            Filters=[{"Name": "vpc-id", "Values": [selected_vpc_id]}]
        )
        subnets = response.get("Subnets", [])

        if len(subnets) < 2:
            print(f"Error: VPC {selected_vpc_id} has fewer than 2 subnets available.")
            return

        subnet_choices = []
        for subnet in subnets:
            subnet_id = subnet["SubnetId"]
            az = subnet["AvailabilityZone"]
            name = get_tag_value(subnet.get("Tags"))

            if name:
                display_name = f"{name} ({subnet_id}) - {az}"
            else:
                display_name = f"{subnet_id} - {az}"

            subnet_choices.append(Choice(title=display_name, value=subnet_id))

        def validate_subnet_count(selected):
            if len(selected) < 2:
                return "You must select at least 2 subnets."
            if len(selected) > 3:
                return "You cannot select more than 3 subnets."
            return True

        selected_subnets = questionary.checkbox(
            "Select Subnets (Space to select, Enter to confirm):",
            choices=subnet_choices,
            validate=validate_subnet_count,
            instruction="(Select 2 or 3)",
        ).ask()

        if not selected_subnets:
            return

        # ==========================================
        # Step 3: Fetch and Select Security Groups
        # ==========================================
        print(f"Fetching security groups for {selected_vpc_id}...")
        response = ec2.describe_security_groups(
            Filters=[{"Name": "vpc-id", "Values": [selected_vpc_id]}]
        )
        sgs = response.get("SecurityGroups", [])

        if not sgs:
            print("No security groups found for this VPC.")
            return

        sg_choices = []
        for sg in sgs:
            sg_id = sg["GroupId"]
            sg_name = sg["GroupName"]  # 'GroupName' is a standard attribute
            name_tag = get_tag_value(sg.get("Tags"))  # 'Name' tag is optional metadata

            # Display logic: "NameTag (GroupName) - sg-123" or "GroupName - sg-123"
            if name_tag:
                display_name = f"{name_tag} ({sg_name}) - {sg_id}"
            else:
                display_name = f"{sg_name} - {sg_id}"

            sg_choices.append(Choice(title=display_name, value=sg_id))

        selected_sgs = questionary.checkbox(
            "Select Security Groups:",
            choices=sg_choices,
            instruction="(Select at least 1)",
        ).ask()

        if not selected_sgs:
            return

        return {
            "vpc": selected_vpc_id,
            "subnets": selected_subnets,
            "security_groups": selected_sgs,
        }

    except NoCredentialsError:
        print("Error: AWS credentials not found.")
    except ClientError as e:
        print(f"AWS Error: {e}")
    except KeyboardInterrupt:
        print("\nOperation cancelled.")
