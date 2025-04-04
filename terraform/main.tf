provider "aws" {
    region = "us-east-1"
    profile = "terraform"
}

resource "aws_instance" "carbon-ec2" {
    ami = "ami-0c02fb55956c7d316"
    instance_type = "t2.micro"

}

resource "aws_db_instance" "carbon_rds" {
    identifier = "carbon-rds-db"
    engine = "mysql"
    instance_class = "db.t3.micro"
    allocated_storage = 20
    username = "admin" 
    password = "Passw0rd!"
    skip_final_snapshot = true 

}

resource "aws_iam_role" "lambda_exec_role" {
    name = "lamda_exec_role"
    assume_role_policy = jsonencode({
        Version = "2012-10-17",
        Statement = [{
            Action = "sts:AssumeRole",
            Effect = "Allow",
            Principal = {
                Service = "lambda.amazonaws.com"
            }
        }]
    })
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
    role = aws_iam_role.lambda_exec_role.name
    policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"

}

resource "aws_lambda_function" "carbon_lambda" {
    function_name = "carbon-test-lambda"
    role = aws_iam_role.lambda_exec_role.arn
    handler = "index.handler"
    runtime = "nodejs18.x"

    filename = "${path.module}/lambda.zip"
    source_code_hash = filebase64sha256("${path.module}/lambda.zip")
}