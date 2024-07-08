![AWS Architecture for Object Detection](./docs/assets/aws_architecture.png)

We implemented a YOLO-based object detection system, comparing performance between local and AWS cloud deployments.

Key findings:

- Local execution outperformed cloud deployment by 2-3x for a 100-image dataset
- Average inference times: 0.0939s (local) vs 0.7637s (cloud)
- Cloud deployment offers superior scalability for larger workloads
- Comprehensive analysis of transfer times, CPU usage, and system metrics
- Evaluation of cloud providers (AWS, Azure, Genesis Cloud) for ML workloads
- Discussion of real-world deployment challenges in edge computing scenarios

Benchmark:

| Metric                   | Value                              |
|:-------------------------|:-----------------------------------|
| Total Images Processed   | 100                                |
| Total Transfer Time      | 25.3988 seconds                    |
| Average Transfer Time    | 0.2540 seconds                     |
| Average Inference Time   | 0.0939 seconds                     |
| CPU Usage                | 12.4%                              |
| Current CPU Frequency    | 1003.7976 MHz                      |
| Max CPU Frequency        | 3600.0 MHz                         |
| Min CPU Frequency        | 400.0 MHz                          |
| Physical Cores           | 4                                  |
| Total Cores              | 8                                  |
