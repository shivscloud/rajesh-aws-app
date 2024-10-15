from flask import Flask, render_template, request, send_file
import boto3
import pandas as pd
import io
from botocore.exceptions import NoCredentialsError, PartialCredentialsError

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    try:
        # Establish an AWS session using the provided credentials
        session = boto3.Session(
            aws_access_key_id=username,
            aws_secret_access_key=password,
            region_name='us-east-1'
        )
        
        # Create clients for the services
        ec2_client = session.client('ec2')
        sts_client = session.client('sts')
        s3_client = session.client('s3')
        elbv2_client = session.client('elbv2')
        lambda_client = session.client('lambda')

        # Fetch the identity of the user
        identity = sts_client.get_caller_identity()
        user_arn = identity['Arn']
        user_name = user_arn.split('/')[-1]

        # Get the list of EC2 instances
        instances = ec2_client.describe_instances()
        instance_data = []
        for reservation in instances['Reservations']:
            for instance in reservation['Instances']:
                instance_data.append({
                    'ResourceType': 'EC2 Instance',
                    'InstanceId': instance['InstanceId'],
                    'InstanceType': instance['InstanceType'],
                    'State': instance['State']['Name'],
                    'PublicIpAddress': instance.get('PublicIpAddress', 'N/A')
                })

        # Get the list of VPCs
        vpcs = ec2_client.describe_vpcs()
        vpc_data = []
        for vpc in vpcs['Vpcs']:
            vpc_data.append({
                'ResourceType': 'VPC',
                'VpcId': vpc['VpcId'],
                'State': vpc['State'],
                'CidrBlock': vpc['CidrBlock']
            })

        # Get the list of S3 buckets
        s3_buckets = s3_client.list_buckets()
        bucket_data = []
        for bucket in s3_buckets['Buckets']:
            bucket_data.append({
                'ResourceType': 'S3 Bucket',
                'BucketName': bucket['Name'],
                'CreationDate': bucket['CreationDate'].strftime('%Y-%m-%d %H:%M:%S')
            })

        # Get the list of ALBs
        load_balancers = elbv2_client.describe_load_balancers()
        alb_data = []
        for lb in load_balancers['LoadBalancers']:
            alb_data.append({
                'ResourceType': 'Application Load Balancer',
                'LoadBalancerArn': lb['LoadBalancerArn'],
                'State': lb['State']['Code'],
                'DNSName': lb['DNSName']
            })

        # Get the list of NLBs
        nlb_data = []
        nlb_list = elbv2_client.describe_load_balancers()
        for nlb in nlb_list['LoadBalancers']:
            if nlb['Type'] == 'network':
                nlb_data.append({
                    'ResourceType': 'Network Load Balancer',
                    'LoadBalancerArn': nlb['LoadBalancerArn'],
                    'State': nlb['State']['Code'],
                    'DNSName': nlb['DNSName']
                })

        # Get the list of Lambda functions
        lambda_functions = lambda_client.list_functions()
        lambda_data = []
        for function in lambda_functions['Functions']:
            lambda_data.append({
                'ResourceType': 'Lambda Function',
                'FunctionName': function['FunctionName'],
                'Runtime': function['Runtime'],
                'State': function['State']
            })

        # Combine all resources into one list
        all_resources = instance_data + vpc_data + bucket_data + alb_data + nlb_data + lambda_data

        # Pass the username and all resources data to the template
        return render_template('resources.html', resources=all_resources, username=user_name)

    except (NoCredentialsError, PartialCredentialsError):
        return "Invalid AWS credentials. Please try again.", 401

@app.route('/download_csv')
def download_csv():
    # Get the data passed to the CSV download request
    resources = request.args.getlist('resource_data[]')

    # Prepare the data for CSV
    resource_list = []
    for resource in resources:
        resource_details = resource.split(',')
        resource_list.append({
            'ResourceType': resource_details[0],
            'Identifier': resource_details[1],
            'State': resource_details[2] if len(resource_details) > 2 else '',
            'AdditionalInfo': resource_details[3] if len(resource_details) > 3 else ''
        })

    # Create a DataFrame and save as CSV
    df = pd.DataFrame(resource_list)
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)

    return send_file(
        io.BytesIO(csv_buffer.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name='aws_resources.csv'
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
