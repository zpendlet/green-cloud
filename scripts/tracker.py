###############################
# AWS Carbon-Emissions Tracker v1.0
# Tracks EC2, RDS, and Lambda usage and estimates energy + emissions
# By: Zoe Pendleton
###############################

import boto3
import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict

#######################
# Utility Functions
#######################

def calculate_uptime_hours(launch_time: datetime) -> float:
    now = datetime.now(timezone.utc)
    return (now - launch_time).total_seconds() / 3600

def calculate_emissions(energy_kwh: float, emission_factor: float = 0.392) -> float:
    return energy_kwh * emission_factor

#######################
# Power Maps
#######################

def load_power_map_ec2(filepath="ec2_power_data.json") -> dict:
    with open(filepath, 'r') as f:
        data = json.load(f)
    return {entry["instanceType"]: entry['watts'] for entry in data}

def load_power_map_rds(filepath="rds_power_data.json") -> dict:
    with open(filepath, 'r') as f:
        data = json.load(f)
    return {entry["instanceClass"]: entry['watts'] for entry in data}

#######################
# EC2 Tracking
#######################

def get_ec2() -> List[Dict]:
    ec2 = boto3.client('ec2') 
    response = ec2.describe_instances()
    if not response["Reservations"]:
        print("No EC2 instances found.")
        return []
    instances = []
    for reservation in response['Reservations']:
        for instance in reservation["Instances"]:
            instances.append(instance)
    return instances 

def estimate_energy_kwh(instance_type: str, uptime_hours: float, power_map: dict, default_watts: float = 20.0) -> float:
    watts = power_map.get(instance_type, default_watts)
    return (watts * uptime_hours) / 1000

#######################
# RDS Tracking
#######################

def get_rds() -> List[Dict]:
    rds = boto3.client('rds')
    response = rds.describe_db_instances()
    if not response["DBInstances"]:
        print("No RDS instances found.")
        return []
    return response["DBInstances"]

def estimate_energy_kwh_rds(instance_class: str, uptime_hours: float, power_map: dict, default_watts: float = 25.0) -> float:
    watts = power_map.get(instance_class, default_watts)
    return (watts * uptime_hours) / 1000

#######################
# Lambda Tracking
#######################

def get_lambda_functions() -> List[Dict]:
    client = boto3.client('lambda')
    functions = []
    paginator = client.get_paginator('list_functions')
    for page in paginator.paginate():
        functions.extend(page['Functions'])
    
    return functions

def get_lambda_metrics(function_name: str, region: str) -> tuple:
    cw = boto3.client('cloudwatch', region_name=region)
    now = datetime.utcnow()
    start = now - timedelta(days=1)

    invocations = cw.get_metric_statistics(
        Namespace='AWS/Lambda',
        MetricName='Invocations',
        Dimensions=[{'Name': 'FunctionName', 'Value': function_name}],
        StartTime=start,
        EndTime=now,
        Period=86400,
        Statistics=['Sum']
    )

    duration = cw.get_metric_statistics(
        Namespace='AWS/Lambda',
        MetricName='Duration',
        Dimensions=[{'Name': 'FunctionName', 'Value': function_name}],
        StartTime=start,
        EndTime=now,
        Period=86400,
        Statistics=['Sum']
    )

    invocations_sum = invocations['Datapoints'][0]['Sum'] if invocations['Datapoints'] else 0
    duration_sum = duration['Datapoints'][0]['Sum'] if duration['Datapoints'] else 0

    return invocations_sum, duration_sum

def estimate_lambda_emissions(invocations: float, duration_ms: float, memory_mb: int, emission_factor: float = 0.392) -> tuple:
    memory_gb = memory_mb / 1024
    energy_kwh = invocations * duration_ms * memory_gb * 0.0000005
    co2e = energy_kwh * emission_factor
    return energy_kwh, co2e

#######################
# Main Function
#######################

def main():
    print("===== EC2 INSTANCES =====")
    instances = get_ec2()
    power_map_ec2 = load_power_map_ec2()

    for instance in instances:
        instance_id = instance["InstanceId"]
        instance_type = instance["InstanceType"]
        launch_time = instance["LaunchTime"]
        region = instance["Placement"]["AvailabilityZone"][:-1]

        uptime_hours = calculate_uptime_hours(launch_time)
        energy_kwh = estimate_energy_kwh(instance_type, uptime_hours, power_map_ec2)
        co2e = calculate_emissions(energy_kwh)

        print(f"\nInstance {instance_id} ({instance_type}) in {region}:")
        print(f"  Uptime: {uptime_hours:.2f} hrs")
        print(f"  Energy used: {energy_kwh:.3f} kWh")
        print(f"  Emissions: {co2e:.2f} kg CO₂e")

    print("\n===== RDS DATABASES =====")
    rds_instances = get_rds()
    power_map_rds = load_power_map_rds()

    for db in rds_instances:
        db_id = db["DBInstanceIdentifier"]
        db_class = db["DBInstanceClass"]
        launch_time = db["InstanceCreateTime"]
        region = db["AvailabilityZone"][:-1]

        uptime_hours = calculate_uptime_hours(launch_time)
        energy_kwh = estimate_energy_kwh_rds(db_class, uptime_hours, power_map_rds)
        co2e = calculate_emissions(energy_kwh)

        print(f"\nRDS Instance {db_id} ({db_class}) in {region}:")
        print(f"  Uptime: {uptime_hours:.2f} hrs")
        print(f"  Energy used: {energy_kwh:.3f} kWh")
        print(f"  Emissions: {co2e:.2f} kg CO₂e")

    print("\n===== LAMBDA FUNCTIONS (24h window) =====")
    lambda_functions = get_lambda_functions()
    if not lambda_functions:
        print("No Lambda functions found.")
        return


    for func in lambda_functions:
        function_name = func['FunctionName']
        memory_mb = func['MemorySize']
        region = func['FunctionArn'].split(":")[3]

        invocations, duration_ms = get_lambda_metrics(function_name, region)
        energy_kwh, co2e = estimate_lambda_emissions(invocations, duration_ms, memory_mb)

        print(f"\nLambda Function: {function_name}")
        print(f"  Memory: {memory_mb} MB")
        print(f"  Invocations: {invocations}")
        print(f"  Duration: {duration_ms:.2f} ms")
        print(f"  Energy used: {energy_kwh:.6f} kWh")
        print(f"  Emissions: {co2e:.4f} kg CO₂e")

if __name__ == "__main__":
    main()





