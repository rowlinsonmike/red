<h1 style="margin:0" align="center">
  <br>
  <img src="image.jpg" alt="logo" width="400" style="border-radius: 50%; object-fit: cover; width: 400px; height: 400px;">

  <br>
  RED
  <br>
</h1>

<h5 style="margin:0;color:grey;letter-spacing:2px;" align="center">(Really Easy Deployments)
</h5>


<div align="center">
<p style="max-width:700px;" align="center">
    RED is a CLI tool that simplifies deploying containerized applications to AWS. It automates the setup and management of Docker containers, ECR repositories, and AWS Batch compute environments with minimal configuration.</p>
</div>




## What RED Does

RED streamlines the process of:
- **Initializing** a project with AWS infrastructure configuration
- **Deploying** Docker containers to AWS ECR and Batch environments
- **Running** batch jobs with optional payloads
- **Scheduling** recurring jobs with cron expressions
- **Managing** scheduled jobs (view, delete, update)
- **Viewing** job logs

## Installation

```bash
pip install red
```

## Requirements

- AWS credentials configured locally
- Docker installed
- Python 3.12+
- Mac OS

## Use Cases

- **Batch Processing**: Run long-running data processing jobs without managing infrastructure
- **Scheduled Tasks**: Automate recurring jobs with cron scheduling
- **Containerized Workloads**: Deploy any containerized application to AWS
- **Serverless Batch**: Leverage AWS Batch for cost-effective, scalable job execution

# Roadmap

- enter session for actively running Job
  - install ssm cli (mac focused)
  - execute commands to running Job

## Workflow Example

```bash
# 1. Initialize project
red init

# 2. Deploy to AWS
red deploy

# 3. Run a job
red run --payload '{"data": "process_me"}'

# 4. Schedule recurring job
red run --cron

# 5. View logs
red log --latest

# 6. Manage schedules
red cron
red cron --delete

# 7. Clean up
red kill
```

## Commands

### `red init`

Initialize a RED project in your current directory.

**Interactive Setup:**
- Project name (auto-derived from directory name)
- CPU count selection
- Memory size (MB)
- Maximum job timeout (in minutes, 1-20160)
- Public/Private environment choice
- VPC subnet and security group selection

**Creates:**
- `.red` configuration file
- `Dockerfile` template
- `main.py` template

```bash
red init
```

### `red deploy`

Deploy your project to AWS. Builds and pushes Docker image to ECR, then creates/updates the Batch compute environment.

```bash
red deploy
```

### `red run`

Execute a batch job immediately or schedule it for recurring execution.

**Options:**
- `--payload, -p`: JSON payload to pass to the job (default: `{}`)
- `--cron, -c`: Schedule as recurring cron job instead of immediate execution

**Examples:**

Immediate execution:
```bash
red run
red run --payload '{"key": "value"}' -d
```

Immediate execution and output log once done:
```bash
red run
red run --payload '{"key": "value"}'
```

Schedule a recurring job:
```bash
red run --cron
# Then provide:
# - Schedule name
# - AWS cron expression (e.g., "cron(0 12 * * ? *)" for daily at noon)
# - One-time run confirmation
```

### `red cron`

Manage scheduled jobs.

**Options:**
- `--delete, -d`: Delete selected cron jobs

**Examples:**

View all schedules:
```bash
red cron
```

Delete schedules:
```bash
red cron --delete
# Select schedules to delete from interactive menu
```

### `red kill`

Delete the entire RED project or a specific schedule.

**Options:**
- `--schedule, -s`: Delete a specific schedule by name (optional)

**Examples:**

Delete entire project (ECR repo, Batch environment, all schedules):
```bash
red kill
```

Delete a specific schedule:
```bash
red kill --schedule "my-schedule-name"
```

### `red log`

View job logs.

**Options:**
- `--latest, -l`: Get the latest log (default: interactive selection)

**Examples:**

View latest log:
```bash
red log --latest
```

Select and view a specific log:
```bash
red log
```

## Configuration

RED stores configuration in a `.red` file created during `red init`. This includes:
- Project name
- CPU and memory specifications
- Job timeout
- VPC and security group settings
- IAM policies for AWS access



# Customization

The following configurations are supported in the `.red` json file.

> \*REQUIRED means property is only required for one of the compute types

<div>
<pre>
{
  "Name": <a href="##name">...</a> (REQUIRED),
  "Timeout": <a href="##timeout">300</a> (REQUIRED),
  "MemorySize": <a href="##memory-size">128</a> (REQUIRED),
  "Cpu": <a href="##cpu">1</a> (*REQUIRED),
  "IamPolicy": <a href="##iam-policy">{...}</a> (OPTIONAL),
  "Env": <a href="##environment-variables">{...}</a> (OPTIONAL),
  "Vpc": <a href="##vpc">{...}</a> (*OPTIONAL),
  "Arch": <a href="##architectures">x86_64</a> (OPTIONAL),
}
</pre>
</div>

## Name

> The name shouldn't contain special characters or spaces

The name used to create all the required resources.


## Timeout

The maximum time in seconds that the container can run before it is stopped.

> Default: 300
>
> Maximum: 900

## CPU

Configue vCPU allotment

Available Options - Reference

## Memory Size

The amount of memory available to the container at runtime. Increasing the memory also increases its CPU allocation. The default value is `128 MB`. The value can be any multiple of `1 MB`.

> Minimum: 128
>
> Maximum: 10240

## Iam Policy

This provides your executions with custom permissions via an IAM policy.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
      "Resource": ["*"]
    }
  ]
}
```

## Environment Variables

You can specify environment variables as key value pairs.

```json
{
  "myvar": "test"
}
```

## VPC

> You must run `kill` command and redeploy if this configuration is updated. Make sure the subnets being deployed into have internet access (nat gateway or igw). If you are using the batch environment you **MUST** specify VPC settings.

```json
{
  "SubnetIds": ["subnet-123123"],
  "SecurityGroupIds": ["sg-123123"]
}
```

Make sure to provide an `IamPolicy` in the configuration with permissions similar to:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:CreateNetworkInterface",
        "ec2:DescribeNetworkInterfaces",
        "ec2:DeleteNetworkInterface"
      ],
      "Resource": "*"
    }
  ]
}
```

## Architectures

If you're building on a Mac with Apple Silicon, ensure you specify `arm64`. The default is `x86_64`. Available options are:

```json
["x86_64", "arm64"]
```

## Public Ip

Assign a public IP to container

Available Options

```json
["ENABLED", "DISABLED"]
```
