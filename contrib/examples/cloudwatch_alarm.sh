#!/bin/sh

ENDPOINT=${1:-http://localhost:8080}
KEY=${2:-demo-key}

curl -XPOST -H "Authorization: Key ${KEY}" "${ENDPOINT}/webhooks/cloudwatch" -H "Content-type: application/json" -d '
{
  "Type" : "Notification",
  "MessageId" : "c820d48d-f681-5419-9c18-9984930fed9e",
  "TopicArn" : "arn:aws:sns:eu-west-1:496780030265:alarm-critical",
  "Subject" : "ALARM: \"cpu-alarm\" in EU - Ireland",
  "Message" : "{\"AlarmName\":\"cpu-alarm2\",\"AlarmDescription\":\"CPU high\",\"AWSAccountId\":\"496780030265\",\"NewStateValue\":\"ALARM\",\"NewStateReason\":\"Threshold Crossed: 1 datapoint (0.0) was greater than or equal to the threshold (-1.0).\",\"StateChangeTime\":\"2014-12-15T22:40:14.144+0000\",\"Region\":\"EU - Ireland\",\"OldStateValue\":\"INSUFFICIENT_DATA\",\"Trigger\":{\"MetricName\":\"lijlCPUUtilization\",\"Namespace\":\"AWS/EC2\",\"Statistic\":\"MINIMUM\",\"Unit\":null,\"Dimensions\":[{\"name\":\"InstanceId\",\"value\":\"i-0c678beb\"}],\"Period\":60,\"EvaluationPeriods\":1,\"ComparisonOperator\":\"GreaterThanOrEqualToThreshold\",\"Threshold\":-1.0}}",
  "Timestamp" : "2014-12-15T22:40:14.205Z",
  "SignatureVersion" : "1",
  "Signature" : "PONAXvCcwSG7P9JmfpdIj2b58DcMZDbd0lUJqKG6RG9b01BVfh44fzWe4di2gRxqwy9Mv9ffErvkqXOuWImfHAM0mEi4KY7KsJPpwOtDSN8LnsKaNgeEmdFyx3D8IENGriMbzA2E8vyh4ZU81nsV9nnxTFJ3ZWUTJres6Q/CxgqWV9UGZsZVbeRhzZ2yrvWluhGpOAf5thbB73PSOb8KzSMnzA+rbYY8XWXlNeNd5ltE4q3PArhGC6IFhl9PrgEWGKG/Pq9K1CH5upVJsQRrCTfOuSjTLKmNFqX8NmjlNweT6ayee4Dme/bljMV0FLF29X2NKzefst7Zoh/ZhiZxOg==",
  "SigningCertURL" : "https://sns.eu-west-1.amazonaws.com/SimpleNotificationService-d6d679a1d18e95c2f9ffcf11f4f9e198.pem",
  "UnsubscribeURL" : "https://sns.eu-west-1.amazonaws.com/?Action=Unsubscribe&SubscriptionArn=arn:aws:sns:eu-west-1:496780030265:alarm-critical:1aa2580b-ebbf-4b58-b883-39a7f6805bc8"
}'
