#!/bin/bash
# Summary Bot NG - Deployment Setup Script
# This script helps set up deployment for various platforms

set -e

echo "=================================="
echo "Summary Bot NG - Deployment Setup"
echo "=================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check if .env exists
if [ ! -f .env ]; then
    print_warning ".env file not found. Creating from template..."
    cp .env.example .env
    print_success "Created .env file. Please edit it with your credentials."
    echo ""
    echo "Required variables:"
    echo "  - DISCORD_TOKEN"
    echo "  - OPENROUTER_API_KEY"
    echo ""
    read -p "Press enter to continue after updating .env..."
fi

# Validate required environment variables
echo "Validating environment variables..."
source .env

if [ -z "$DISCORD_TOKEN" ]; then
    print_error "DISCORD_TOKEN not set in .env"
    exit 1
fi

if [ -z "$OPENROUTER_API_KEY" ]; then
    print_error "OPENROUTER_API_KEY not set in .env"
    exit 1
fi

print_success "Environment variables validated"
echo ""

# Deployment platform selection
echo "Select deployment platform:"
echo "1) Docker (local)"
echo "2) Railway"
echo "3) Render"
echo "4) Fly.io"
echo "5) Skip platform setup"
echo ""
read -p "Enter choice [1-5]: " platform_choice

case $platform_choice in
    1)
        echo ""
        echo "=== Docker Deployment ==="

        # Check if Docker is installed
        if ! command -v docker &> /dev/null; then
            print_error "Docker not installed. Please install Docker first."
            exit 1
        fi

        if ! command -v docker-compose &> /dev/null; then
            print_error "Docker Compose not installed. Please install Docker Compose first."
            exit 1
        fi

        print_success "Docker and Docker Compose found"

        # Build and start
        echo ""
        echo "Building Docker image..."
        docker-compose build

        echo ""
        echo "Starting services..."
        docker-compose up -d

        echo ""
        print_success "Services started successfully!"
        echo ""
        echo "View logs: docker-compose logs -f"
        echo "Stop services: docker-compose down"
        echo "Health check: curl http://localhost:5000/health"
        ;;

    2)
        echo ""
        echo "=== Railway Deployment ==="

        # Check if Railway CLI is installed
        if ! command -v railway &> /dev/null; then
            print_warning "Railway CLI not found. Installing..."
            npm install -g @railway/cli
        fi

        print_success "Railway CLI found"

        echo ""
        echo "Logging in to Railway..."
        railway login

        echo ""
        echo "Initializing Railway project..."
        railway init

        echo ""
        echo "Setting environment variables..."
        railway variables set DISCORD_TOKEN="$DISCORD_TOKEN"
        railway variables set OPENROUTER_API_KEY="$OPENROUTER_API_KEY"
        railway variables set LLM_ROUTE="openrouter"

        echo ""
        read -p "Deploy now? (y/n): " deploy_now
        if [ "$deploy_now" = "y" ]; then
            echo "Deploying to Railway..."
            railway up
            print_success "Deployment initiated!"
        else
            echo "Skipping deployment. Run 'railway up' when ready."
        fi
        ;;

    3)
        echo ""
        echo "=== Render Deployment ==="
        print_warning "Render deployment is configured via render.yaml"
        echo ""
        echo "Next steps:"
        echo "1. Go to https://dashboard.render.com"
        echo "2. Click 'New +' → 'Blueprint'"
        echo "3. Connect your GitHub repository"
        echo "4. Select render.yaml"
        echo "5. Add environment variables in dashboard"
        echo ""
        echo "Required environment variables:"
        echo "  - DISCORD_TOKEN"
        echo "  - OPENROUTER_API_KEY"
        ;;

    4)
        echo ""
        echo "=== Fly.io Deployment ==="

        # Check if flyctl is installed
        if ! command -v flyctl &> /dev/null; then
            print_warning "Fly CLI not found. Installing..."
            curl -L https://fly.io/install.sh | sh
            echo 'export FLYCTL_INSTALL="$HOME/.fly"' >> ~/.bashrc
            echo 'export PATH="$FLYCTL_INSTALL/bin:$PATH"' >> ~/.bashrc
            source ~/.bashrc
        fi

        print_success "Fly CLI found"

        echo ""
        echo "Logging in to Fly.io..."
        flyctl auth login

        echo ""
        echo "Creating Fly.io app..."
        flyctl launch --no-deploy

        echo ""
        echo "Setting secrets..."
        flyctl secrets set DISCORD_TOKEN="$DISCORD_TOKEN"
        flyctl secrets set OPENROUTER_API_KEY="$OPENROUTER_API_KEY"

        echo ""
        echo "Creating persistent volume..."
        flyctl volumes create summarybot_data --size 1

        echo ""
        read -p "Deploy now? (y/n): " deploy_now
        if [ "$deploy_now" = "y" ]; then
            echo "Deploying to Fly.io..."
            flyctl deploy
            print_success "Deployment initiated!"
        else
            echo "Skipping deployment. Run 'flyctl deploy' when ready."
        fi
        ;;

    5)
        print_warning "Skipping platform setup"
        ;;

    *)
        print_error "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "=================================="
print_success "Setup complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo "  - Check deployment documentation: docs/DEPLOYMENT.md"
echo "  - Review security guide: docs/SECURITY.md"
echo "  - Set up monitoring and alerts"
echo "  - Configure GitHub Actions secrets"
echo ""
