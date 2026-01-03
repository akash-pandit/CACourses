#!/usr/bin/bash

# Exports all or specified lambda functions (specified by parent directory) to AWS Lambda.
# e.g. `bash deploy-lambdas.sh func-name` packages function ./func-name/lambda_function.py
# with the production dependencies specified in ./pyproject.toml into a zip file and pushes
# them to AWS lambda with the credentials of whoever is logged into aws on the executor's
# shell.

# Config: constants
shopt -s nullglob
ROLE_NAME="cacourses-lambda-role"
REGION="us-west-1"
DEPENDENCIES_DIR="./dependencies"
DEPENDENCIES_FILE="./requirements.txt"
LAMBDA_DIRS="*/lambda_function.py"

# Config: utility functions
log () { echo "$(date '+[%H:%M:%S]') deploy-lambdas.sh: $1"; }
err () { echo "$(date '+[%H:%M:%S]') ERROR: deploy-lambdas.sh: $1" >&2; exit 1; }

# Validation: required dependencies installed (uv, aws) & configured (aws login)
which uv > /dev/null
[[ $? -ne 0 ]] && err "Please install the package manager uv (https://docs.astral.sh/uv/getting-started/installation/)"
which aws > /dev/null
[[ $? -ne 0 ]] && err "Please install & login to the aws cli (https://aws.amazon.com/cli/)"
aws sts get-caller-identity > /dev/null 2>&1
[[ $? -ne 0 ]] && err "Invalid/missing login for aws, please log in to the aws cli"

# Validation: required files
[[ -z $LAMBDA_DIRS ]] && err "No lambda directories (./*/lambda_function.py) found."
[[ ! -f "pyproject.toml" ]] && err "pyproject.toml not found."
[[ ! -f "trust-policy.json" ]] && echo '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}' > trust-policy.json

[[ $# -ne 0 ]] && dirs=$@ || dirs=* 

# Extract production dependencies from pyproject.toml

log "Exporting/installing dependencies..."
uv export --no-dev -q -o $DEPENDENCIES_FILE
uv pip install -q -r $DEPENDENCIES_FILE \
    --target $DEPENDENCIES_DIR \
    --python-platform x86_64-manylinux2014 \
    --link-mode copy
rm -r $DEPENDENCIES_FILE

# Create lambda zip packages
for dir in $dirs; do
    if [[ -d "$dir" ]] && [[ -f "$dir/lambda_function.py" ]]; then
        rm "$dir/lambda.zip"
        if [[ -d "$DEPENDENCIES_DIR" ]]; then
            (cd "$DEPENDENCIES_DIR" && zip -rq "../$dir/lambda.zip" .)
        fi
        (cd "$dir" && zip -g -rq "lambda.zip" "lambda_function.py")
        log "Packaged $(basename $dir) and dependencies into zip"
    fi
done
rm -r $DEPENDENCIES_DIR

# Check for existence of AWS Lambda access role 'cacourses-lambda-role'

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ROLE_ARN="arn:aws:iam::$AWS_ACCOUNT_ID:role/$ROLE_NAME"

log "Checking for IAM role: $ROLE_NAME"
aws iam get-role --role-name "$ROLE_NAME" > /dev/null 2>&1

if [[ $? -ne 0 ]]; then  # If the role does not exist, create it and give it minimally necessary permissions (attach a policy)
    log "Role not found, creating $ROLE_NAME with basic execution policy..."

    aws iam create-role --role-name "$ROLE_NAME" \
        --assume-role-policy-document file://trust-policy.json \
        > /dev/null 2>&1
    aws iam attach-role-policy --role-name "$ROLE_NAME" \
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole \
        > /dev/null 2>&1
    
    log "Role created successfully. Waiting for IAM propagation..."

    aws iam get-role --role-name "$ROLE_NAME" > /dev/null 2>&1
    while [ $? -ne 0 ]; do
        sleep 1
        aws iam get-role --role-name "$ROLE_NAME" > /dev/null 2>&1
    done
else
    log "Found existing role: $ROLE_NAME"
fi

# Create / update lambda functions with given policy


for dir in $dirs; do
    if [[ -d "$dir" ]] && [[ -f "$dir/lambda_function.py" ]]; then
        funcname="$(basename $dir)"
        zipfp="$dir/lambda.zip"
        envstr=$(tr '\n' ',' < .env | sed 's/,$//')

        aws lambda get-function --function-name "$funcname" > /dev/null 2>&1
        if [[ $? -eq 0 ]]; then

            log "Updating existing function $funcname"

            aws lambda update-function-code \
                --function-name "$funcname" \
                --zip-file "fileb://$zipfp" \
                > /dev/null

            [[ $? -ne 0 ]] && err "update-function-code $funcname failed." || log "update-function-code $funcname succeeded."
            sleep 5  # race cond

            aws lambda update-function-configuration \
                --function-name "$funcname" \
                --role $ROLE_ARN \
                --environment Variables={$envstr} \
                > /dev/null
            
            [[ $? -ne 0 ]] && err "update-function-configuration $funcname failed." || log "update-function-configuration $funcname succeeded."

            log "Updated lambda function $funcname"

        else

            aws lambda create-function \
                --function-name "$funcname" \
                --role $ROLE_ARN \
                --runtime python3.12 \
                --handler lambda_function.lambda_handler \
                --environment Variables={$(tr '\n' ',' < .env)} \
                --region us-west-1 \
                --zip-file fileb://$dir/lambda.zip \
                > /dev/null

            [[ $? -ne 0 ]] && err "create-function with $funcname failed."

            log "Setting up Public Function URL for $funcname..."
    
            aws lambda create-function-url-config \
                --function-name "$funcname" \
                --auth-type NONE \
                --invoke-mode BUFFERED \
                --region "$REGION" \
                > /dev/null
            
            [[ $? -ne 0 ]] && err "create-function-url-config with $funcname failed."

            aws lambda add-permission \
                --function-name "$funcname" \
                --statement-id FunctionURLAllowPublicAccess \
                --action lambda:InvokeFunctionUrl \
                --principal "*" \
                --function-url-auth-type NONE \
                --region "$REGION" \
                > /dev/null

            [[ $? -ne 0 ]] && err "add-permission (lambda:InvokeFunctionURL) with $funcname failed."

            aws lambda add-permission \
                --function-name "$funcname" \
                --statement-id FunctionURLAllowInvokeAction \
                --action lambda:InvokeFunction \
                --principal "*" \
                --source-auth-type NONE \
                --region "$REGION" \
                > /dev/null

            [[ $? -ne 0 ]] && err "add-permission (lambda:InvokeFunction) with $funcname failed."

            URL=$(aws lambda get-function-url-config --function-name "$funcname" --query FunctionUrl --output text)

            log "Created lambda function $funcname with url $URL"
        fi
    fi
done
log "All lambdas updated :)"
