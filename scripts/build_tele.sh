# Run this script from the folder with Dockerfile
#! /bin/zsh
set -e

APP_NAME=tele_service

INSTANCE_NAME=telegram_rag
PROJECT_NAME=telegram_rag
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --output text | cut -f 1)
AWS_REGION=$(aws configure get region)

ECR_URL=${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com
VERSION_TAG=$(poetry version -s --dry-run)
VERSIONED_IMAGE="$PROJECT_NAME:$APP_NAME-$VERSION_TAG"
IMAGE_URL="$ECR_URL/$VERSIONED_IMAGE"

docker buildx build . -t $VERSIONED_IMAGE --build-arg service_name=${APP_NAME} --ssh default=$HOME/.ssh/id_rsa
docker tag $VERSIONED_IMAGE $IMAGE_URL

aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_URL
docker push $IMAGE_URL

INSTANCE_IP=$(aws ec2 describe-instances \
--region us-east-1 \
--filters "Name=tag:Name,Values=$INSTANCE_NAME" "Name=instance-state-name,Values=running" \
--query "Reservations[*].Instances[*].{PublicIpAddress:PublicIpAddress}" \
--output json  | jq -r '.[0][0].PublicIpAddress')

echo "SSH-ing into $INSTANCE_IP"

# SSH into the EC2 instance and execute commands
ssh -i ~/.ssh/ec2-ssh-keypair.pem ubuntu@$INSTANCE_IP << EOF
    set -e
    aws configure export-credentials
    # Step 1: Authenticate Docker to the Amazon ECR registry
    aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_URL
    echo "Pulling from $IMAGE_URL"
    # Step 2: Pull the specified image
    docker pull $IMAGE_URL

    # Step 3: Kill any existing containers of the same base image

    # Step 3: Kill any existing containers of the same base image


    docker stop $APP_NAME || true
    docker rm $APP_NAME || true

    # Optional: create a network bridge for cross-service comms
    if ! docker network inspect $PROJECT_NAME > /dev/null 2>&1; then
        echo "Network $PROJECT_NAME does not exist. Creating..."
        docker network create $PROJECT_NAME
    else
        echo "Network $PROJECT_NAME already exists."
    fi

    # Step 4: Run a new container with the updated image
    echo "Starting container $APP_NAME"
    docker run -d --name $APP_NAME --network $PROJECT_NAME $IMAGE_URL 
EOF