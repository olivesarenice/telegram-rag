
variable "ingress_rules" {
  default = {
    "SSH rule" = {
      "description" = "For SSH"
      "from_port"   = "22"
      "to_port"     = "22"
      "protocol"    = "tcp"
      "cidr_blocks" = ["58.182.22.131/32"]
    },
  }
  type = map(object({
    description = string
    from_port   = number
    to_port     = number
    protocol    = string
    cidr_blocks = list(string)
  }))
  description = "Security group rules"
}



# No need for other ingress as the server is long-polling (sending requests out)
locals {
  envs = { for tuple in regexall("(.*)=(.*)", file("../.env")) : tuple[0] => tuple[1] }
}
