![AWS Architecture for Object Detection](./docs/assets/aws_architecture.png)

We benchmarked local and cloud inference times for YOLO:

- Local execution outperformed cloud deployment by 2-3x for a 100-image dataset
- Average inference times: 0.0939s (local) vs 0.7637s (cloud)
- Cloud infrastructure scales better, but cold start of lambda reduces performance noticeably

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

See full report in `./docs/report.pdf`.
