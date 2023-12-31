import aws_cdk as cdk
import boto3
import json
from deploy.config import config
from constructs import Construct
from aws_cdk import (
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_certificatemanager as acm,
    RemovalPolicy as removalPolicy,
    Stack,
)

class ProteinDCWebsiteS3DeployStack(cdk.Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self._update_website()

        # Define a S3 bucket that contains a static website
        self.s3_bucket = self._create_hosting_s3_bucket()

        # Creates Cloudfront Origin Access Identity to access a restricted S3
        origin_access_identity = cloudfront.OriginAccessIdentity(
            self,
            'cdkTestOriginAccessIdentity',
        )
        self.origin_access_identity = origin_access_identity

        # Allows Origin Access Control to read from S3
        self.s3_bucket.grant_read(origin_access_identity)

        cdk.CfnOutput(
            self, 
            'Website S3 Bucket Name',
            value=self.s3_bucket.bucket_name,
        )

    def _create_hosting_s3_bucket(self):
        """ Returns a S3 instance that serves a static website """
        website_bucket = s3.Bucket(
            self,
            'static-website-for-cdkdemo',
            bucket_name = config.WEB_BUCKET_NAME,
            # website_index_document="index.html",
            removal_policy=removalPolicy.DESTROY,
            access_control=s3.BucketAccessControl.PRIVATE,
        )

        # Populates bucket with files from local file system
        s3deploy.BucketDeployment(
            self,
            'DeployWebsite',
            destination_bucket=website_bucket,
            sources=[
                s3deploy.Source.asset(config.WEB_UPLOAD_FOLDER)
            ],
            retain_on_delete=False,
        )
        return website_bucket

    
    def _update_website(self):
        # Create a Boto3 client for API Gateway
        
        apigateway_client = boto3.client('apigateway', region_name=config.ACCT_REGION)
        stage_name = 'prod'

        # Retrieve the API Gateway details
        api_response = apigateway_client.get_rest_apis()
        api_id = None

        # Find the API Gateway by name
        for api in api_response["items"]:
            if api["name"] == config.AGW_NAME:
                api_id = api["id"]
                break

        if api_id:
            # Get the stage information
            stage_response = apigateway_client.get_stage(
                restApiId=api_id,
                stageName=stage_name
            )

            stage_url = stage_response["stageName"]
            api_url = f"https://{api_id}.execute-api.{config.ACCT_REGION}.amazonaws.com/{stage_url}/"

            print(f'api_url: {api_url}')
            file_path = '../web/config.js'
            js_config_content = {
                "apiEndpointUrl": api_url
            }

            js_config_content_string = json.dumps(js_config_content, indent=2)

            # Open the file in append mode ('a')
            with open(file_path, 'w') as file:
                file.write("\n")  # Add a newline before appending
                file.write(f"const agw_config ={js_config_content_string}")
                file.write("\n")

            print(f'Content has been appended to the file "{file_path}", with content: {js_config_content_string}')
        else:
            print("API Gateway not found.")

    