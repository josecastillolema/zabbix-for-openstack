#!/bin/python

# import modules into Python script
import requests, json, httplib, urllib, urllib2
import xml.etree.ElementTree as ET
import os, sys, subprocess, math
import math, time
from simplejson import scanner
import eventlet
import traceback

# define env incl. DSM IP addr, port & login credentials
DSM_ip = 'x.y.z.w'   #IP address of DSM instance
DSM_port = 'p'         #Default port of DSM instance
DSM_login = 'login'  #Login credentials for DSM
DSM_pass = 'passowrd'   #Password
verify_cert = False       #Default = False
apiversion = '3.0'        #Default = 2.0

class PayloadFilter(object):
    """PayloadFilter

    Simple class for creating filters for interacting with the Dell
    Storage API 15.3 and later.
    """

    def __init__(self, filtertype='AND'):
        self.payload = {}
        self.payload['filter'] = {'filterType': filtertype,
                                  'filters': []}

    def append(self, name, val, filtertype='Equals'):
        if val is not None:
            apifilter = {}
            apifilter['attributeName'] = name
            apifilter['attributeValue'] = val
            apifilter['filterType'] = filtertype
            self.payload['filter']['filters'].append(apifilter)


class HttpClient(object):
    """HttpClient

    Helper for making the REST calls.
    """

    def __init__(self, host, port, user, password, verify, apiversion):
        """HttpClient handles the REST requests.

        :param host: IP address of the Dell Data Collector.
        :param port: Port the Data Collector is listening on.
        :param user: User account to login with.
        :param password: Password.
        :param verify: Boolean indicating whether certificate verification
                       should be turned on or not.
        :param apiversion: Dell API version.
        """
        self.baseUrl = 'https://%s:%s/' % (host, port)

        self.session = requests.Session()
        self.session.auth = (user, password)

        self.header = {}
        self.header['Content-Type'] = 'application/json; charset=utf-8'
        self.header['Accept'] = 'application/json'
        self.header['x-dell-api-version'] = apiversion
        self.verify = verify

        # Verify is a configurable option.  So if this is false do not
        # spam the c-vol log.
        if not verify:
            requests.packages.urllib3.disable_warnings()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.session.close()

    def __formatUrl(self, url):
        baseurl = self.baseUrl
        # Some url sources have api/rest and some don't. Handle.
        if 'api/rest' not in url:
            baseurl += 'api/rest/'
        return '%s%s' % (baseurl, url if url[0] != '/' else url[1:])

    def _get_header(self, async):
        if async:
            header = self.header.copy()
            header['async'] = 'True'
            return header
        return self.header

    def _get_async_url(self, asyncTask):
        """Handle a bug in SC API that gives a full url."""
        try:
            # strip off the https.
            url = asyncTask.get('returnValue').split(
                'https://')[1].split('/', 1)[1]
        except IndexError:
            url = asyncTask.get('returnValue')
        except AttributeError:
            print('_get_async_url: Atttribute Error. (%r)'% asyncTask)
            url = 'api/rest/ApiConnection/AsyncTask/'

        # Blank URL
        if not url:
            print('_get_async_url: No URL. (%r)'% asyncTask)
            url = 'api/rest/ApiConnection/AsyncTask/'

        # Check for incomplete url error case.
        if url.endswith('/'):
            # Try to fix.
            id = asyncTask.get('instanceId')
            if id:
                # We have an id so note the error and add the id.
                pring('_get_async_url: url format error. (%r)'% asyncTask)
                url = url + id
            else:
                # No hope.
                print('_get_async_url: Bogus return async task %r'%
                          asyncTask)
                raise Exception(
                    '_get_async_url: Invalid URL.')

        # Check for an odd error case
        if url.startswith('<') and url.endswith('>'):
            print('_get_async_url: Malformed URL '
                          '(XML returned). (%r)'% asyncTask)
            raise Exception(
                '_get_async_url: Malformed URL.')

        return url

    def _wait_for_async_complete(self, asyncTask):
        url = self._get_async_url(asyncTask)
        while True and url:
            try:
                r = self.get(url)
                # We can leave this loop for a variety of reasons.
                # Nothing returned.
                # r.content blanks.
                # Object returned switches to one without objectType or with
                # a different objectType.
                if not StorageCenterApi._check_result(r):
                    print('Async error:\n'
                              '\tstatus_code: {code}\n'
                              '\ttext:        {text}\n'.format(
                              code= r.status_code,
                               text= r.text))
                else:
                    # In theory we have a good run.
                    if r.content:
                        content = r.json()
                        if content.get('objectType') == 'AsyncTask':
                            url = self._get_async_url(content)
                            eventlet.sleep(1)
                            continue
                    else:
                        print('Async debug: r.content is None')
                return r
            except Exception:
                print("An exception occurred")
                methodname = asyncTask.get('methodName')
                objectTypeName = asyncTask.get('objectTypeName')
                msg = ('Async error: Unable to retrieve %(obj)s '
                         'method %(method)s result'
                       % {'obj': objectTypeName, 'method': methodname})
                raise Exception(msg)
        # Shouldn't really be able to get here.
        print('_wait_for_async_complete: Error asyncTask: %r'% asyncTask)
        return None

    def _rest_ret(self, rest_response, async):
        # If we made an async call and it was accepted
        # we wait for our response.
        if async:
            if rest_response.status_code == 202:
                asyncTask = rest_response.json()
                return self._wait_for_async_complete(asyncTask)
            else:
                print('REST Async error command not accepted:\n'
                          '\tUrl:    {url}\n'
                          '\tCode:   {code}\n'
                          '\tReason: {reason}\n'.format(
                          url= rest_response.url,
                           code= rest_response.status_code,
                           reason= rest_response.reason))
                msg = _('REST Async Error: Command not accepted.')
                raise Exception(msg)
        return rest_response

#    @utils.retry(exceptions=(requests.ConnectionError,
#                             exception.DellDriverRetryableException))
    def get(self, url):
        print('get: {url}'.format( url= url))
        rest_response = self.session.get(self.__formatUrl(url),
                                         headers=self.header,
                                         verify=self.verify)

        if rest_response and rest_response.status_code == 400 and (
                'Unhandled Exception' in rest_response.text):
            raise 
        return rest_response

#    @utils.retry(exceptions=(requests.ConnectionError,))
    def post(self, url, payload, async=False):
        #print('post: {url} data: {payload}'.format(
        #          url= url,
        #           payload= payload))
        return self._rest_ret(self.session.post(
            self.__formatUrl(url),
            data=json.dumps(payload,
                            ensure_ascii=False).encode('utf-8'),
            headers=self._get_header(async),
            verify=self.verify), async)

#    @utils.retry(exceptions=(requests.ConnectionError,))
    def put(self, url, payload, async=False):
        print('put: {url} data: {payload}'.format(
                  url= url,
                   payload= payload))
        return self._rest_ret(self.session.put(
            self.__formatUrl(url),
            data=json.dumps(payload,
                            ensure_ascii=False).encode('utf-8'),
            headers=self._get_header(async),
            verify=self.verify), async)

#    @utils.retry(exceptions=(requests.ConnectionError,))
    def delete(self, url, payload=None, async=False):
        print('delete: {url} data: {payload}'.format(
                  url= url, payload= payload))
        named = {'headers': self._get_header(async), 'verify': self.verify}
        if payload:
            named['data'] = json.dumps(
                payload, ensure_ascii=False).encode('utf-8')

        return self._rest_ret(
            self.session.delete(self.__formatUrl(url), **named), async)


class StorageCenterApi(object):

    APIDRIVERVERSION = '1.0.0'
    def __init__(self, host=DSM_ip, port=DSM_port, user=DSM_login, password=DSM_pass, verify=verify_cert, apiversion=apiversion):
        """This creates a connection to Dell SC or EM.

        :param host: IP address of the REST interface..
        :param port: Port the REST interface is listening on.
        :param user: User account to login with.
        :param password: Password.
        :param verify: Boolean indicating whether certificate verification
                       should be turned on or not.
        :param apiversion: Version used on login.
        """
        self.notes = 'Created by Dell Cinder Driver'
        self.repl_prefix = 'Cinder repl of '
        self.ssn = None
        # primaryssn is the ssn of the SC we are configured to use. This
        # doesn't change in the case of a failover.
        self.primaryssn = None
        self.failed_over = False
        self.vfname = 'vol'
        self.sfname = 'srv'
        self.excluded_domain_ips = []
        self.legacypayloadfilters = False
        self.consisgroups = True
        self.protocol = 'Iscsi'
        self.apiversion = apiversion
        # Nothing other than Replication should care if we are direct connect
        # or not.
        self.is_direct_connect = False
        connection = requests.Session()
        connection.auth = (user, password)
        self.client = HttpClient(host, port, user, password,
                                 verify, apiversion)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close_connection()

    def open_connection(self):
        """Authenticate with Dell REST interface.

        :raises: VolumeBackendAPIException.
        """
        # Set our fo state.
        self.failed_over = (self.primaryssn != self.ssn)

        # Login
        payload = {}
        payload['Application'] = 'API REST Driver'
        payload['ApplicationVersion'] = self.APIDRIVERVERSION
        r = self.client.post('ApiConnection/Login', payload)
        if not self._check_result(r):
            # SC requires a specific version. See if we can get it.
            r = self._check_version_fail(payload, r)
            # Either we tried to login and have a new result or we are
            # just checking the same result. Either way raise on fail.
            if not self._check_result(r):
                raise Exception(
                    'Failed to connect to Dell REST API')

        # We should be logged in.  Try to grab the api version out of the
        # response.
        try:
            apidict = self._get_json(r)
            version = apidict['apiVersion']
            self.is_direct_connect = apidict['provider'] == 'StorageCenter'
            splitver = version.split('.')
            if splitver[0] == '2':
                if splitver[1] == '0':
                    self.consisgroups = False
                    self.legacypayloadfilters = True

                elif splitver[1] == '1':
                    self.legacypayloadfilters = True
            return

        except Exception:
            # Good return but not the login response we were expecting.
            # Log it and error out.
            print('Unrecognized Login Response: %s'% r)

    def close_connection(self):
        """Logout of Dell REST API."""
        r = self.client.post('ApiConnection/Logout', {})
        # 204 expected.
        self._check_result(r)
        self.client = None

    def _get_payload_filter(self, filterType='AND'):
        return PayloadFilter(filterType)

    def _search_for_volume(self, name):
        """Search self.ssn for volume of name.

        This searches the folder self.vfname (specified in the cinder.conf)
        for the volume first.  If not found it searches the entire array for
        the volume.

        :param name: Name of the volume to search for.  This is the cinder
                     volume ID.
        :returns: Dell Volume object or None if not found.
        :raises VolumeBackendAPIException: If multiple copies are found.
        """
        #print('Searching {sn} for {name}'.format(
        #          sn= self.ssn,
        #           name= name))

        # Cannot find a volume without the name.
        if name is None:
            return None

        # Look for our volume in our folder.
        vollist = self._get_volume_list(name, None, True)
        # If an empty list was returned they probably moved the volumes or
        # changed the folder name so try again without the folder.
        if not vollist:
            print('Cannot find volume {n} in {v}.  Searching SC.'.format(
                      n= name,
                       v= self.vfname))
            vollist = self._get_volume_list(name, None, False)

        # If multiple volumes of the same name are found we need to error.
        if len(vollist) > 1:
            # blow up
            msg = ('Multiple copies of volume %s found.') % name
            raise Exception(msg)

        # We made it and should have a valid volume.
        return None if not vollist else vollist[0]

    def _get_volume_list(self, name, deviceid, filterbyvfname=True, ssn=-1):
        """Return the specified list of volumes.

        :param name: Volume name.
        :param deviceid: Volume device ID on the SC backend.
        :param filterbyvfname:  If set to true then this filters by the preset
                                folder name.
        :param ssn: SSN to search on.
        :return: Returns the scvolume list or None.
        """
        ssn = self._vet_ssn(ssn)
        result = None
        # We need a name or a device ID to find a volume.
        if name or deviceid:
            pf = self._get_payload_filter()
            pf.append('scSerialNumber', ssn)
            if name is not None:
                pf.append('Name', name)
            if deviceid is not None:
                pf.append('DeviceId', deviceid)
            # set folderPath
            if filterbyvfname:
                vfname = (self.vfname if self.vfname.endswith('/')
                          else self.vfname + '/')
                pf.append('volumeFolderPath', vfname)
            r = self.client.post('StorageCenter/ScVolume/GetList', pf.payload)
            if self._check_result(r):
                result = self._get_json(r)
        # We return None if there was an error and a list if the command
        # succeeded. It might be an empty list.
        return result

    def _get_json(self, blob):
        """Returns a dict from the JSON of a REST response.

        :param blob: The response from a REST call.
        :returns: JSON or None on error.
        """
        try:
            return blob.json()
        except AttributeError:
            LOG.error(_LE('Error invalid json: %s'),
                      blob)
        except TypeError as ex:
            LOG.error(_LE('Error TypeError. %s'), ex)
        except scanner.JSONDecodeError as ex:
            LOG.error(_LE('Error JSONDecodeError. %s'), ex)
        # We are here so this went poorly. Log our blob.
        print('_get_json blob %s'% blob)
        return None

    def _get_id(self, blob):
        """Returns the instanceId from a Dell REST object.

        :param blob: A Dell SC REST call's response.
        :returns: The instanceId from the Dell SC object or None on error.
        """
        try:
            if isinstance(blob, dict):
                return blob.get('instanceId')
        except AttributeError:
            print('Invalid API object: %s'%blob)
        except TypeError as ex:
            print('Error TypeError. %s'%ex)
        except scanner.JSONDecodeError as ex:
            print('Error JSONDecodeError. %s'%ex)
        print('_get_id failed: blob %s'% blob)
        return None

    def _vet_ssn(self, ssn):
        """Returns the default if a ssn was not set.

        Added to support live volume as we aren't always on the primary ssn
        anymore

        :param ssn: ssn to check.
        :return: Current ssn or the ssn sent down.
        """
        if ssn == -1:
            return self.ssn
        return ssn

    @staticmethod
    def _check_result(rest_response):
        """Checks and logs API responses.

        :param rest_response: The result from a REST API call.
        :returns: ``True`` if success, ``False`` otherwise.
        """
        if rest_response is not None:
            if 200 <= rest_response.status_code < 300:
                # API call was a normal success
                return True

            # Some versions return this as a dict.
            try:
                response_json = rest_response.json()
                response_text = response_json.text['result']
            except Exception:
                # We do not care why that failed. Just use the text.
                response_text = rest_response.text

            print('REST call result:\n'
                      '\tUrl:    {url}\n'
                      '\tCode:   {code}\n'
                      '\tReason: {reason}\n'
                      '\tText:   {text}'.format(
                      url= rest_response.url,
                       code= rest_response.status_code,
                       reason= rest_response.reason,
                       text= response_text))
        else:
            print('Failed to get REST call result.')
        return False

if __name__ == "__main__":

    connection = StorageCenterApi()
    connection.open_connection()
  
    s = subprocess.check_output("sudo virsh list | grep inst | awk {' print $2 '}", shell=True).split('\n')[:-1]

    mps = subprocess.check_output('sudo multipath -ll | grep COMPELNT,Compellent', shell=True).split('\n')[:-1]
    multipaths = {}
    for mp in mps:
        mpsplit = mp.split()
        multipaths[mpsplit[2]]=mpsplit[1][1:-1]
    for vm in s:
        vmxml = ET.fromstring(subprocess.check_output('sudo virsh dumpxml %s ' % vm, shell=True))
        for disk in vmxml.find('devices').findall('disk'):
            try:
                serial_srv = multipaths[disk.find('source').get('dev').split('/')[-1]]
                serial_dsm = connection._search_for_volume(disk.find('serial').text)['deviceId']
                if not (serial_srv in serial_dsm) and not (serial_dsm in serial_srv):
                    print 1
                    sys.exit()
            except:
                #print vm
                #print ET.tostring(disk)
                #traceback.print_exc()
                pass
    
    print 0

