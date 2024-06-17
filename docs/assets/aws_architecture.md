```
                        process image
 trigger lambda      ┌─────────────────┐       store results
      ┌──────────────► Lambda Function ├────────────┐
      │              └─────────────────┘            │
┌─────┴─────┐                                  ┌────▼─────┐
│ S3 Bucket │                                  │ DynamoDB │
└─────▲─────┘                                  └────┬─────┘
      │                                             │
      │                                             │
      │                                             │
      │                                             │
      │                                             ▼
 upload image                                  look up results
```
