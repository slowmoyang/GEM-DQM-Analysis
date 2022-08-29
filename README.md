# GEM DQM Analysis

## Prerequisite
### CERN GRID User Certificate 
Issue a passwordless grid user certificiate at https://ca.cern.ch/ca/
```zsh
export CERN_CERTIFICATE_PATH=~/private
mkdir -p ${CERN_CERTIFICATE_PATH}
openssl pkcs12 -clcerts -nokeys -in ./myCertificate.p12 -out ${CERN_CERTIFICATE_PATH}/usercert.pem
openssl pkcs12 -nocerts -in ./myCertificate.p12 -out ${CERN_CERTIFICATE_PATH}/userkey.tmp.pem
openssl rsa -in ${CERN_CERTIFICATE_PATH}/userkey.tmp.pem -out ${CERN_CERTIFICATE_PATH}/userkey.pem
rm ./myCertificate.p12 ${CERN_CERTIFICATE_PATH}/userkey.tmp.pem
```

### App with access permission on OMS API
- Create an application at https://application-portal.web.cern.ch, and request an access permission on OMS API. (See [this guideline](https://gitlab.cern.ch/cmsoms/oms-api-client/-/wikis/uploads/01fe5b10560e76849ce636cf53e59e20/OMS_CERN_OpenID_API__2022_.pdf))

### Python environment
```zsh
conda env create -n environment.yaml
```
