SERVER_DIR="/home/ubuntu/api"

AWS_REGION="ap-southeast-1"
AWS_ACCOUNT_ID="797671034027"
ECR_REPO="ikon-backend"
ECR_REGISTRY="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
ECR_IMAGE="$ECR_REGISTRY/$ECR_REPO:latest"

echo "Logging in to ECR"
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY

echo "Building docker image"
docker build --no-cache --target production -t $ECR_IMAGE .

echo "Pushing docker image to ECR at $(date '+%Y-%m-%d %H:%M:%S')"
docker push $ECR_IMAGE

echo "Ensure server directory exists"
ssh ikon "mkdir -p $SERVER_DIR"

echo "Copy docker-compose.prod.yml to server"
scp -o IdentitiesOnly=yes -o StrictHostKeyChecking=no docker-compose.prod.yml ikon:$SERVER_DIR/docker-compose.prod.yml

echo "Deploying to server"
ssh ikon bash -s << EOF

aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY

cd $SERVER_DIR

docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml pull
IMAGE_TAG=latest docker compose -f docker-compose.prod.yml up -d

sleep 10

docker exec lifechoice_web_prod python manage.py migrate
docker exec lifechoice_web_prod python manage.py collectstatic --noinput

echo "Deployment complete at $(date '+%Y-%m-%d %H:%M:%S')"
docker ps



EOF
