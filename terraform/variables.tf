variable "aws_region" {
  description = "AWS region for every resource"
  type        = string
  default     = "ap-south-1"
}

variable "owner" {
  description = "Tag value identifying who owns (and must destroy) these resources"
  type        = string
  default     = "raj-prakash"
}

variable "cluster_name" {
  description = "EKS cluster name; also used as the name prefix for the network"
  type        = string
  default     = "clinicflow-eks"
}

variable "kubernetes_version" {
  description = "EKS control-plane version"
  type        = string
  default     = "1.34"
}

variable "vpc_cidr" {
  description = "Address space of the VPC"
  type        = string
  default     = "10.21.0.0/16"
}

variable "az_count" {
  description = "Availability zones to spread the subnets over (EKS needs at least two)"
  type        = number
  default     = 2

  validation {
    condition     = var.az_count >= 2 && var.az_count <= 3
    error_message = "EKS requires subnets in at least two AZs; this layout supports two or three."
  }
}

variable "enable_nat_gateway" {
  description = "true: worker nodes in private subnets behind one NAT gateway. false: no NAT/EIP cost, nodes in public subnets."
  type        = bool
  default     = true
}

variable "node_instance_types" {
  description = "Instance types for the managed node group"
  type        = list(string)
  default     = ["t3.medium"]
}

variable "node_desired_size" {
  type    = number
  default = 2
}

variable "node_min_size" {
  type    = number
  default = 1
}

variable "node_max_size" {
  type    = number
  default = 3
}

variable "api_allowed_cidrs" {
  description = "Who may reach the public Kubernetes API endpoint. Narrow this to your own IP (x.x.x.x/32)."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}
