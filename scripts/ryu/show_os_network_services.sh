export OS_USERNAME=admin
export OS_USER_DOMAIN_NAME=Default
export OS_PROJECT_DOMAIN_NAME=Default
export OS_TENANT_NAME=admin
export NOVA_VERSION=1.1
export OS_PROJECT_NAME=admin
export OS_PROJECT_ID=123
export OS_PASSWORD=password
export OS_NO_CACHE=True
export COMPUTE_API_VERSION=1.1
export no_proxy=,openstack.com.br
export OS_CLOUDNAME=overcloud
export OS_AUTH_URL=https://openstack.com.br:13000/v3
export OS_IDENTITY_API_VERSION=3
export OS_INTERFACE=public
export PYTHONWARNINGS="ignore:Certificate has no, ignore:A true SSLContext object is not available"
/usr/bin/openstack network agent list | grep UP | grep XXX > /dev/null
echo $?

