#!/bin/bash

# Input file containing key-value pairs
INPUT_FILE="input.txt"

# Destination AWS credentials file
CREDENTIALS_FILE="$HOME/.aws/credentials"

# Initialize variables
ACCESS_KEY=""
SECRET_KEY=""
SESSION_TOKEN=""

vault write account/131097458262/sts/Owner ttl=60m > $INPUT_FILE

# Function to read key-value pairs from the input file
read_key_value() {
    while IFS= read -r line; do
        # Skip empty lines and lines with only delimiters
        if [[ -z "$line" || "$line" =~ ^[-]*$ ]]; then
            continue
        fi

        # Split the line by the first occurrence of whitespace
        key=$(echo "$line" | awk '{print $1}')
        value=$(echo "$line" | cut -d' ' -f2- | xargs)

        # Assign values to corresponding variables
        case "$key" in
            access_key) ACCESS_KEY="$value" ;;
            secret_key) SECRET_KEY="$value" ;;
            session_token) SESSION_TOKEN="$value" ;;
        esac
    done < "$INPUT_FILE"
}

# Function to generate the AWS credentials file
generate_credentials_file() {
    # Ensure the .aws directory exists
    mkdir -p "$(dirname "$CREDENTIALS_FILE")"

    # Create or overwrite the AWS credentials file
    cat > "$CREDENTIALS_FILE" <<EOL
[default]
aws_access_key_id = $ACCESS_KEY
aws_secret_access_key = $SECRET_KEY
aws_session_token = $SESSION_TOKEN
EOL

    echo "AWS credentials have been generated and saved to $CREDENTIALS_FILE."
}

# Call the functions
read_key_value
generate_credentials_file

