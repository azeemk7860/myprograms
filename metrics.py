import boto3
import json
import jmespath
from datetime import datetime, date, time, timedelta

"""
This program retrieves the AWS metrics using the AWS boto3 api. 
Requirements 
1) install Python
2) install boto3 using 'pip install boto3'
3) Install jmespath using 'pip install jmespath'
4) aws_access_key_id, aws_secret_access_key, region are stored in credentials file in the the users .aws directory 
"""

#Handle datetime data coming from the boto3 api json results
def dt_converter(o):
    if isinstance(o, datetime):
        return o.__str__()

# return the correct metric unit for ec2 for the metric in question
def get_ec2_unit(metric):
    if metric == 'CPUUtilization':
        return 'Percent'
    elif metric == 'DiskReadBytes' or metric == 'DiskWriteBytes':
        return 'Bytes'
    else:
        return 'Count'

# return the correct metric unit for ebs for the metric in question
def get_ebs_unit(metric):
    if metric == 'VolumeIdleTime' or metric == 'VolumeTotalReadTime' or metric == 'VolumeTotalWriteTime':
        return 'Seconds'
    elif metric == 'VolumeWriteOps' or metric == 'VolumeReadOps':
        return 'Count'
    elif metric == 'VolumeReadBytes' or metric == 'VolumeWriteBytes':
        return 'Bytes'
    elif metric == 'BurstBalance':
        return 'Percent'

# retrieve the ec2 isntances for in the current AWS account
def get_ec2_resources(instance_details_list):
    ec2 = boto3.client('ec2')
    response = ec2.describe_instances()
    #print(json.dumps(response, indent=4, default=dt_converter))
    jmes = "Reservations[*].Instances[*].InstanceId[]"
    # print(jmespath.search(jmes, response))
    for instance in jmespath.search(jmes, response):
        instance_details_list.append(instance)
    # print(instance_details_list)
    return instance_details_list

# Parse the datetime from AWS json results to a human readable date time
def parse_timestamp(timestamps):
    new_list = []
    for i in range(len(timestamps)):
        new_list.append(timestamps[i].strftime('%Y-%m-%d %H:%M:%S'))
    return new_list


#Retrive the ec2 metrics
def get_ec2_metrics():
    instance_list = []
    ec2_metric_list = ['CPUUtilization', 'DiskReadBytes', 'DiskWriteBytes', 'DiskReadOps', 'DiskWriteOps',
                       'NetworkPacketsIn', 'NetworkPacketsOut', 'CPUCreditUsage', 'CPUCreditBalance']

    #get all the instances in the current aws account
    get_ec2_resources(instance_list)

    #get cloudwatch client
    cloudwatch = boto3.client('cloudwatch')

    #Retrive metrics for each instance and each metric
    for instance in instance_list:
        for metric in ec2_metric_list:
            response = cloudwatch.get_metric_data(
                MetricDataQueries=[
                    {
                        'Id': instance.replace('-', '_'),
                        'MetricStat': {
                            'Metric': {
                                'Namespace': 'AWS/EC2',
                                'MetricName': metric,
                                'Dimensions': [
                                    {
                                        'Name': 'InstanceId',
                                        'Value': instance,
                                    },
                                ]
                            },
                            'Period': 300,
                            'Stat': 'Average',
                            'Unit': get_ec2_unit(metric)
                        },
                    },
                ],
                StartTime=datetime.utcnow() - timedelta(minutes=60),
                EndTime=datetime.utcnow(),
            )
            # print(json.dumps(response, indent=4, default=dt_converter))
            print('Instance:', instance, 'Metric:', metric, )

            timestamps = "MetricDataResults[*].Timestamps[]"
            tval = jmespath.search(timestamps, response)
            list_tval = parse_timestamp(tval)
            print('TimeStamps', list_tval)

            values = "MetricDataResults[*].Values[]"
            vval = jmespath.search(values, response)
            print('Values', vval)
            print('-------------------------------------------------------------')

#Retrive the ebs volume id of all the volumes in the current aws account
def get_ebs_volumes():
    ec2 = boto3.client('ec2')
    response = ec2.describe_instances()
    #print(json.dumps(response, indent=4, default=dt_converter))

    jmes = "Reservations[*].Instances[*].BlockDeviceMappings[*].Ebs.VolumeId[]"
    # print(jmespath.search(jmes, response))
    tt = jmespath.search(jmes, response)
    return tt[0]

#Retrive the ebs metrics
def get_ebs_metrics():
    ebs_volumes = get_ebs_volumes()

    ebs_metric_list = ['VolumeIdleTime', 'VolumeWriteOps', 'VolumeReadBytes', 'VolumeTotalReadTime',
                       'VolumeTotalWriteTime', 'VolumeReadOps', 'VolumeWriteBytes']

    cloudwatch = boto3.client('cloudwatch')

    for volume in ebs_volumes:
        for metric in ebs_metric_list:
            #print('Getting metric:', metric)
            response = cloudwatch.get_metric_data(
                MetricDataQueries=[
                    {
                        'Id': 'm1',
                        'MetricStat': {
                            'Metric': {
                                'Namespace': 'AWS/EBS',
                                'MetricName': metric,
                                'Dimensions': [
                                    {
                                        'Name': 'VolumeId',
                                        'Value': volume,
                                    },
                                ]
                            },
                            'Period': 300,
                            'Stat': 'Average',
                            'Unit': get_ebs_unit(metric)
                        },
                    },
                ],
                StartTime=datetime.utcnow() - timedelta(minutes=60),
                EndTime=datetime.utcnow(),
            )
            # print(json.dumps(response, indent=4, default=dt_converter))
            print('Volume:', volume, 'Metric:', metric, 'Unit:', get_ebs_unit(metric))
            timestamps = "MetricDataResults[*].Timestamps[]"
            tval = jmespath.search(timestamps, response)
            list_tval = parse_timestamp(tval)
            print('TimeStamps', list_tval)
            values = "MetricDataResults[*].Values[]"
            vval = jmespath.search(values, response)
            print('Values', vval)
            print('-------------------------------------------------------------')


"""
Retrieve the cloudwatch agent metrics. This requires cloudwatch agent installed, configured and started to send metrics to cloudwatch
"""
def get_cw_agent_metrics():
    cw_metric_list = ['disk_used_percent','mem_used_percent']
    cloudwatch = boto3.client('cloudwatch')
    met = cloudwatch.list_metrics()
    #print(len(cwa))

    for list in cw_metric_list:
        jmes = "Metrics[?Namespace=='CWAgent' && MetricName=='" + list + "']"
        cwa = jmespath.search(jmes, met)
        #print(json.dumps(cwa, indent=4, default=dt_converter))
        for metric in cwa:
            #print('Getting metric:', metric)
            response = cloudwatch.get_metric_data(
                MetricDataQueries=[
                    {
                        'Id': 'm1',
                        'MetricStat': {
                            'Metric':
                                metric
                            ,
                            'Period': 300,
                            'Stat': 'Average',
                            'Unit': 'Percent'
                        },
                    },
                ],
                StartTime=datetime.utcnow() - timedelta(minutes=60),
                EndTime=datetime.utcnow(),
            )
            # print(json.dumps(response, indent=4, default=dt_converter))
            print('Metric:', metric)
            timestamps = "MetricDataResults[*].Timestamps[]"
            tval = jmespath.search(timestamps, response)
            list_tval = parse_timestamp(tval)
            print('TimeStamps', list_tval)

            values = "MetricDataResults[*].Values[]"
            vval = jmespath.search(values, response)
            print('Values', vval)
            print('-------------------------------------------------------------')


get_ec2_metrics()
get_ebs_metrics()
get_cw_agent_metrics()