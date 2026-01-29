
import boto3
import os

print(f"AWS_PROFILE: {os.environ.get('AWS_PROFILE')}")
print(f"AWS_REGION: {os.environ.get('AWS_REGION')}")
print(f"AWS_DEFAULT_REGION: {os.environ.get('AWS_DEFAULT_REGION')}")

try:
    print("Attempting to create STS client...")
    sts = boto3.client('sts')
    print("STS client created.")
    print("Calling get_caller_identity...")
    identity = sts.get_caller_identity()
    print(f"Identity: {identity}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
