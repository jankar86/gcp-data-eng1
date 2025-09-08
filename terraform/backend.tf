terraform {
  backend "gcs" {
    bucket = "data-eng-d-tf-state"
    prefix = "envs/prod"   # change per environment if you add more later
  }
}
