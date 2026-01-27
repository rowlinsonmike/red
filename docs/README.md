<h1 style="margin:0" align="center">
  <br>
  <img src="image.png" alt="logo" width="400" style="border-radius: 50%; object-fit: cover; width: 400px; height: 400px;">

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


> 🎉 RED 2.0 is out! 
> This update refocuses the CLI solely on AWS Batch. This descision allows focused development and quality improvements on the Batch ecosystem.




## What RED Does

RED streamlines the process of:
- **Initializing** a project with AWS infrastructure configuration
- **Deploying** Docker containers to AWS ECR and Batch environments
- **Running** batch jobs with optional payloads
- **Scheduling** recurring jobs with cron expressions
- **Managing** scheduled jobs (view, delete)
- **Viewing** job logs

## Installation

```bash
pip install pip install https://github.com/rowlinsonmike/red/raw/refs/heads/main/dist/red-2.0.0.tar.gz
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

## Roadmap

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



# .red file

The following configurations are supported in the `.red` json file.

<div>
<pre>
    {
      "Name": <a href="##name">...</a>,
      "VPC": <a href="##vpc">{...}</a>,
      "Arch": <a href="##architectures">x86_64</a>,
      "Cpu": <a href="##cpu">...</a>,
      "MemorySize": <a href="##memory-size">...</a>,
      "StorageSize": <a href="##storage-size">...</a>,
      "Timeout": <a href="##timeout">...</a>,
      "assignPublicIp": "<a href="##public-ip">...</a>,
      "IamPolicy": <a href="##iam-policy">{...}</a>
      "Envs": <a href="##environment-variables">{...}</a>
    }

</pre>
</div>

## Name

The name used to create all required resources. The name cannot contain special characters or spaces


## Timeout

The maximum time in minutes that the container can run before it is stopped.

> Default: 1
>
> Maximum: 10000

## Storage Size

The alloted ephermal storage for each job in GB

> Minimum: 21
>
> Maximum: 200

## CPU

Configue vCPU allotment. See [AWS docs](https://docs.aws.amazon.com/batch/latest/APIReference/API_ResourceRequirement.html) for valid values.

## Memory Size

Configue memory allotment. See [AWS docs](https://docs.aws.amazon.com/batch/latest/APIReference/API_ResourceRequirement.html) for valid values.

## Iam Policy

This provides your jobs with custom permissions via an IAM policy.

## Environment Variables

You can specify environment variables as key value pairs.

```json
{
  "myvar": "test"
}
```

## VPC

> You must terminate and recreate your RED deployment if this changes. Make sure the subnets being deployed into have internet access (nat gateway or igw).

```json
{
  "SubnetIds": ["subnet-123123"],
  "SecurityGroupIds": ["sg-123123"]
}
```

## Architectures

If you're building on a Mac with Apple Silicon, ensure you specify `arm64`. The default is `x86_64`. Available options are:

```json
["x86_64", "arm64"]
```

## Public Ip

Assign a public IP to container. Available options are:

```json
["ENABLED", "DISABLED"]
```
