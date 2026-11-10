"""Generate a reviewable CloudFormation template. No AWS mutation on import/run."""
import json
from pathlib import Path

def ref(name): return {'Ref':name}
def attr(name,key): return {'Fn::GetAtt':[name,key]}
def role(service, policies):
    return {'Type':'AWS::IAM::Role','Properties':{
        'AssumeRolePolicyDocument':{'Version':'2012-10-17','Statement':[{'Effect':'Allow',
            'Principal':{'Service':service},'Action':'sts:AssumeRole'}]},
        'ManagedPolicyArns':['arn:aws:iam::aws:policy/'+p for p in policies]}}

def template():
    resources = {
      'ClusterRole':role('eks.amazonaws.com',['AmazonEKSClusterPolicy']),
      'NodeRole':role('ec2.amazonaws.com',['AmazonEKSWorkerNodePolicy','AmazonEC2ContainerRegistryReadOnly','AmazonEKS_CNI_Policy']),
      'Cluster':{'Type':'AWS::EKS::Cluster','Properties':{
        'Name':'classroom-main','Version':'1.36','RoleArn':attr('ClusterRole','Arn'),
        'UpgradePolicy':{'SupportType':'STANDARD'},
        'AccessConfig':{'AuthenticationMode':'API_AND_CONFIG_MAP','BootstrapClusterCreatorAdminPermissions':True},
        'ResourcesVpcConfig':{'SubnetIds':ref('PublicSubnets'),'EndpointPrivateAccess':True,
                             'EndpointPublicAccess':True,'PublicAccessCidrs':['0.0.0.0/0']},
        'Logging':{'ClusterLogging':{'EnabledTypes':[{'Type':'api'},{'Type':'audit'},{'Type':'authenticator'}]}},
        'Tags':[{'Key':'Purpose','Value':'week11-shared-team1-team8'}]}},
      'LaunchTemplate':{'Type':'AWS::EC2::LaunchTemplate','Properties':{'LaunchTemplateData':{
        'MetadataOptions':{'HttpTokens':'required','HttpPutResponseHopLimit':1},
        'CreditSpecification':{'CpuCredits':'standard'},
        'BlockDeviceMappings':[{'DeviceName':'/dev/xvda','Ebs':{'VolumeSize':30,'VolumeType':'gp3','Encrypted':True,'DeleteOnTermination':True}}]}}},
      'Nodes':{'Type':'AWS::EKS::Nodegroup','Properties':{
        'ClusterName':ref('Cluster'),'NodegroupName':'classroom-shared','NodeRole':attr('NodeRole','Arn'),
        'Subnets':ref('PublicSubnets'),'InstanceTypes':['t3.large'],'AmiType':'AL2023_x86_64_STANDARD',
        'CapacityType':'ON_DEMAND','ScalingConfig':{'MinSize':1,'DesiredSize':1,'MaxSize':1},
        'LaunchTemplate':{'Id':ref('LaunchTemplate'),'Version':attr('LaunchTemplate','LatestVersionNumber')},
        'UpdateConfig':{'MaxUnavailable':1},'Labels':{'purpose':'classroom'},
        'Tags':{'Environment':'main','Purpose':'week11-shared-team1-team8'}}},
      'PrivateRoutes':{'Type':'AWS::EC2::RouteTable','Properties':{'VpcId':ref('VpcId')}},
      'GatewaySg':{'Type':'AWS::EC2::SecurityGroup','Properties':{
        'GroupDescription':'Only the classroom Lightsail reverse proxy reaches the internal NLB','VpcId':ref('VpcId'),
        'SecurityGroupIngress':[{'IpProtocol':'tcp','FromPort':80,'ToPort':80,'CidrIp':'172.26.7.237/32'}]}},
      'GatewayNlb':{'Type':'AWS::ElasticLoadBalancingV2::LoadBalancer','Properties':{
        'Name':'classroom-main-gateway','Type':'network','Scheme':'internal',
        'Subnets':[ref('PrivateSubnetA'),ref('PrivateSubnetB')],'SecurityGroups':[ref('GatewaySg')],
        'LoadBalancerAttributes':[{'Key':'load_balancing.cross_zone.enabled','Value':'true'}]}},
      'GatewayTargets':{'Type':'AWS::ElasticLoadBalancingV2::TargetGroup','Properties':{
        'VpcId':ref('VpcId'),'Protocol':'TCP','Port':30080,'TargetType':'instance',
        'HealthCheckProtocol':'HTTP','HealthCheckPath':'/healthz','HealthCheckPort':'30080',
        'TargetGroupAttributes':[{'Key':'deregistration_delay.timeout_seconds','Value':'30'}]}},
      'GatewayListener':{'Type':'AWS::ElasticLoadBalancingV2::Listener','Properties':{
        'LoadBalancerArn':ref('GatewayNlb'),'Port':80,'Protocol':'TCP',
        'DefaultActions':[{'Type':'forward','TargetGroupArn':ref('GatewayTargets')}]}},
      'AllowGatewayNodes':{'Type':'AWS::EC2::SecurityGroupIngress','Properties':{
        'GroupId':attr('Cluster','ClusterSecurityGroupId'),'IpProtocol':'tcp','FromPort':30080,'ToPort':30080,
        'SourceSecurityGroupId':ref('GatewaySg')}},
      'GithubRole':{'Type':'AWS::IAM::Role','Properties':{
        'RoleName':'classroom-github-main-example',
        'AssumeRolePolicyDocument':{'Version':'2012-10-17','Statement':[{
          'Effect':'Allow','Principal':{'Federated':ref('GithubProviderArn')},'Action':'sts:AssumeRoleWithWebIdentity',
          'Condition':{'StringEquals':{'token.actions.githubusercontent.com:aud':'sts.amazonaws.com',
                                     'token.actions.githubusercontent.com:sub':'repo:MinQDU014/idea-support-server:environment:main'}}}]},
        'Policies':[{'PolicyName':'ExampleImageAndClusterOnly','PolicyDocument':{'Version':'2012-10-17','Statement':[
          {'Effect':'Allow','Action':['ecr:GetAuthorizationToken'],'Resource':'*'},
          {'Effect':'Allow','Action':['ecr:BatchCheckLayerAvailability','ecr:InitiateLayerUpload','ecr:UploadLayerPart',
             'ecr:CompleteLayerUpload','ecr:PutImage','ecr:BatchGetImage','ecr:GetDownloadUrlForLayer','ecr:DescribeImages'],
           'Resource':'arn:aws:ecr:ap-southeast-2:950177940921:repository/idea-support-server'},
          {'Effect':'Allow','Action':'eks:DescribeCluster','Resource':attr('Cluster','Arn')}
        ]}}]}},
      'GithubAccess':{'Type':'AWS::EKS::AccessEntry','Properties':{
        'ClusterName':ref('Cluster'),'PrincipalArn':attr('GithubRole','Arn'),
        'Type':'STANDARD','KubernetesGroups':['classroom:team']}},
    }
    for name, az, cidr in [('A','a','172.31.48.0/24'),('B','b','172.31.49.0/24')]:
        resources['PrivateSubnet'+name]={'Type':'AWS::EC2::Subnet','Properties':{
            'VpcId':ref('VpcId'),'AvailabilityZone':'ap-southeast-2'+az,'CidrBlock':cidr,
            'MapPublicIpOnLaunch':False,'Tags':[{'Key':'Name','Value':'classroom-main-internal-'+az}]}}
        resources['PrivateRoute'+name]={'Type':'AWS::EC2::SubnetRouteTableAssociation','Properties':{
            'SubnetId':ref('PrivateSubnet'+name),'RouteTableId':ref('PrivateRoutes')}}
    return {'AWSTemplateFormatVersion':'2010-09-09','Description':'One shared classroom EKS; one 8GB worker; no NAT, no SSH',
      'Parameters':{'VpcId':{'Type':'AWS::EC2::VPC::Id','Default':'vpc-0b4718526b088dd9b'},
        'PublicSubnets':{'Type':'List<AWS::EC2::Subnet::Id>','Default':'subnet-0acb6bbac7d18223f,subnet-05307aef95ca85c1a'},
        'GithubProviderArn':{'Type':'String'}},'Resources':resources,
      'Outputs':{'ClusterName':{'Value':ref('Cluster')},'GithubRoleArn':{'Value':attr('GithubRole','Arn')},
        'NodeGroup':{'Value':ref('Nodes')},'GatewayDns':{'Value':attr('GatewayNlb','DNSName')},
        'TargetGroupArn':{'Value':ref('GatewayTargets')}}}

if __name__=='__main__':
    output = Path(__file__).with_name('eks-cloudformation.json')
    output.write_text(json.dumps(template(),indent=2)+'\n')
    print('Prepared '+str(output)+'; no resources created.')
