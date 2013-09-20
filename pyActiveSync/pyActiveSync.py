########################################################################
#  Copyright (C) 2013 Sol Birnbaum
# 
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
# 
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
# 
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA  02110-1301, USA.
########################################################################

# Code Playground

import sys

from utils.as_code_pages import as_code_pages
from utils.wbxml import wbxml_parser
from utils.wapxml import wapxmltree, wapxmlnode
from client.as_connect import as_connect
from client.storage import storage

from client.FolderSync import FolderSync
from client.Sync import Sync
from client.GetItemEstimate import GetItemEstimate
from client.ResolveRecipients import ResolveRecipients
from client.FolderCreate import FolderCreate
from client.FolderUpdate import FolderUpdate
from client.FolderDelete import FolderDelete
from client.Ping import Ping
from client.MoveItems import MoveItems
from client.Provision import Provision
from client.ItemOperations import ItemOperations
from client.ValidateCert import ValidateCert

from objects.MSASCMD import FolderHierarchy, as_status

from proto_creds import * #create a file proto_creds.py with vars: as_server, as_user, as_pass

pyver = sys.version_info

storage.create_db_if_none()
conn, curs = storage.get_conn_curs()
device_info = {"Model":"%d.%d.%d" % (pyver[0], pyver[1], pyver[2]), "IMEI":"123456", "FriendlyName":"My pyAS Client", "OS":"Python", "OSLanguage":"en-us", "PhoneNumber": "NA", "MobileOperator":"NA", "UserAgent": "pyAS"}

#create wbxml_parser test
parser = wbxml_parser(as_code_pages.build_as_code_pages())

#create activesync connector
as_conn = as_connect(as_server) #e.g. "as.myserver.com"
as_conn.set_credential(as_user, as_pass)
as_conn.options()
policykey = storage.get_keyvalue("X-MS-PolicyKey")
if policykey:
    as_conn.set_policykey(policykey)

def as_request(cmd, wapxml_req):
    print "\r\n%s Request:" % cmd
    print wapxml_req
    res = as_conn.post(cmd, parser.encode(wapxml_req))
    wapxml_res = parser.decode(res)
    print "\r\n%s Response:" % cmd
    print wapxml_res
    return wapxml_res

#Provision functions
def do_apply_eas_policies(policies):
    for policy in policies.keys():
        print "Virtually applying %s = %s" % (policy, policies[policy])
    return True

def do_provision():
    provision_xmldoc_req = Provision.build("0", device_info)
    as_conn.set_policykey("0")
    provision_xmldoc_res = as_request("Provision", provision_xmldoc_req)
    status, policystatus, policykey, policytype, policydict, settings_status = Provision.parse(provision_xmldoc_res)
    as_conn.set_policykey(policykey)
    storage.update_keyvalue("X-MS-PolicyKey", policykey)
    storage.update_keyvalue("EASPolicies", repr(policydict))
    if do_apply_eas_policies(policydict):
        provision_xmldoc_req = Provision.build(policykey)
        provision_xmldoc_res = as_request("Provision", provision_xmldoc_req)
        status, policystatus, policykey, policytype, policydict, settings_status = Provision.parse(provision_xmldoc_res)
        if status == "1":
            as_conn.set_policykey(policykey)
            storage.update_keyvalue("X-MS-PolicyKey", policykey)

#FolderSync + Provision
foldersync_xmldoc_req = FolderSync.build(storage.get_synckey("0"))
foldersync_xmldoc_res = as_request("FolderSync", foldersync_xmldoc_req)
changes, synckey, status = FolderSync.parse(foldersync_xmldoc_res)
if int(status) > 138 and int(status) < 145:
    print as_status("FolderSync", status)
    do_provision()
    foldersync_xmldoc_res = as_request("FolderSync", foldersync_xmldoc_req)
    changes, synckey, status = FolderSync.parse(foldersync_xmldoc_res)
    if int(status) > 138 and int(status) < 145:
        print as_status("FolderSync", status)
        raise Exception("Unresolvable provisoning error: %s. Cannot continue..." % status)
if len(changes) > 0:
    storage.update_folderhierarchy(changes)
    storage.update_synckey(synckey, "0", curs)
    conn.commit()

#ItemOperations
itemoperations_params = [{"Name":"Fetch","Store":"Mailbox", "FileReference":"%34%67%32"}]
itemoperations_xmldoc_req = ItemOperations.build(itemoperations_params)
print "\r\nItemOperations Request:\r\n", itemoperations_xmldoc_req
#itemoperations_xmldoc_res, attachment_file = as_conn.fetch_multipart(itemoperations_xmldoc_req, "myattachment1.txt")
#itemoperations_xmldoc_res_parsed = ItemOperations.parse(itemoperations_xmldoc_res)
#print itemoperations_xmldoc_res

#FolderCreate
parent_folder = storage.get_folderhierarchy_folder_by_name("Inbox", curs)
new_folder = FolderHierarchy.Folder(parent_folder[0], "TestFolder1", str(FolderHierarchy.FolderCreate.Type.Mail))
foldercreate_xmldoc_req = FolderCreate.build(storage.get_synckey("0"), new_folder.ParentId, new_folder.DisplayName, new_folder.Type)
foldercreate_xmldoc_res = as_request("FolderCreate", foldercreate_xmldoc_req)
foldercreate_res_parsed = FolderCreate.parse(foldercreate_xmldoc_res)
if foldercreate_res_parsed[0] == "1":
    new_folder.ServerId = foldercreate_res_parsed[2]
    storage.insert_folderhierarchy_change(new_folder, curs)
    storage.update_synckey(foldercreate_res_parsed[1], "0", curs)
    conn.commit()

#FolderUpdate
old_folder_name = "TestFolder1"
new_folder_name = "TestFolder2"
#new_parent_id = parent_folder = storage.get_folderhierarchy_folder_by_name("Inbox", curs)
folder_row = storage.get_folderhierarchy_folder_by_name(old_folder_name, curs)
update_folder = FolderHierarchy.Folder(folder_row[1], new_folder_name, folder_row[3], folder_row[0])
folderupdate_xmldoc_req = FolderUpdate.build(storage.get_synckey("0"), update_folder.ServerId, update_folder.ParentId, update_folder.DisplayName)
folderupdate_xmldoc_res = as_request("FolderUpdate", folderupdate_xmldoc_req)
folderupdate_res_parsed = FolderUpdate.parse(folderupdate_xmldoc_res)
if folderupdate_res_parsed[0] == "1":
    new_folder.DisplayName = new_folder_name
    storage.update_folderhierarchy_change(new_folder, curs)
    storage.update_synckey(folderupdate_res_parsed[1], "0", curs)
    conn.commit()

#FolderDelete
folder_name = "TestFolder2"
folder_row = storage.get_folderhierarchy_folder_by_name(folder_name, curs)
delete_folder = FolderHierarchy.Folder()
delete_folder.ServerId = folder_row[0]
folderdelete_xmldoc_req = FolderDelete.build(storage.get_synckey("0"), delete_folder.ServerId)
folderdelete_xmldoc_res = as_request("FolderDelete", folderdelete_xmldoc_req)
folderdelete_res_parsed = FolderDelete.parse(folderdelete_xmldoc_res)
if folderdelete_res_parsed[0] == "1":
    storage.delete_folderhierarchy_change(delete_folder, curs)
    storage.update_synckey(folderdelete_res_parsed[1], "0", curs)
    conn.commit()

#ResolveRecipients
resolverecipients_xmldoc_req = ResolveRecipients.build("zebra")
resolverecipients_xmldoc_res = as_request("ResolveRecipients", resolverecipients_xmldoc_req)

#Sync function
def do_sync(collection_ids):
    as_sync_xmldoc_req = Sync.build(storage.get_synckeys_dict(curs), collection_ids)
    print "\r\nRequest:"
    print as_sync_xmldoc_req
    res = as_conn.post("Sync", parser.encode(as_sync_xmldoc_req))
    print "\r\nResponse:"
    if res == '':
        print "Nothing to Sync!"
    else:
        as_sync_xmldoc_res = parser.decode(res)
        print as_sync_xmldoc_res
        sync_res = Sync.parse(as_sync_xmldoc_res)
        storage.update_emails(sync_res)

#GetItemsEstimate
def do_getitemestimates(collection_ids):
    getitemestimate_xmldoc_req = GetItemEstimate.build(storage.get_synckeys_dict(curs), collection_ids)
    getitemestimate_xmldoc_res = as_request("GetItemEstimate", getitemestimate_xmldoc_req)

    getitemestimate_res = GetItemEstimate.parse(getitemestimate_xmldoc_res)
    return getitemestimate_res

def getitemestimate_check_prime_collections(getitemestimate_responses):
    has_synckey = []
    needs_synckey = []
    for response in getitemestimate_responses:
        if response.Status == "1":
            has_synckey.append(response.CollectionId)
        if response.Status == "2":
            print "GetItemEstimate Status: Unknown CollectionId (%s) specified. Removing." % response.CollectionId
        if response.Status == "3":
            print "GetItemEstimate Status: Sync needs to be primed."
            needs_synckey.append(response.CollectionId)
            has_synckey.append(response.CollectionId) #technically *will* have synckey after do_sync() need end of function
    if len(needs_synckey) > 0:
        do_sync(needs_synckey)
    return has_synckey, needs_synckey

#Ping (push), GetItemsEstimate and Sync process test
#Ping
ping_xmldoc_req = Ping.build("60", [("5", "Email"),("10","Email")]) #5=Inbox,10=Sent Items
ping_xmldoc_res = as_request("Ping", ping_xmldoc_req)
ping_res = Ping.parse(ping_xmldoc_res)
if ping_res[0] == "2": #2=New changes available
    getitemestimate_responses = do_getitemestimates(ping_res[3])

    has_synckey, just_got_synckey = getitemestimate_check_prime_collections(getitemestimate_responses)

    if (len(has_synckey) < ping_res[3]) or (len(just_got_synckey) > 0): #grab new estimates, since they changed
        getitemestimate_responses = do_getitemestimates(has_synckey)

    collections_to_sync = [] 

    for response in getitemestimate_responses:
        if response.Status == "1":
            if int(response.Estimate) > 0:
                collections_to_sync.append(response.CollectionId)
        else:
            print "GetItemEstimate Status (error): %s, CollectionId: %s." % (response.Status, response.CollectionId)

    if len(collections_to_sync) > 0:
        do_sync(collections_to_sync)

##MoveItems
#moveitems_xmldoc_req = MoveItems.build([("5:24","5","10")])
#moveitems_xmldoc_res = as_request("MoveItems", moveitems_xmldoc_req)
#moveitems_res = MoveItems.parse(moveitems_xmldoc_res)
#for moveitem_res in moveitems_res:
#    if moveitem_res[1] == "3":
#        storage.update_email({"server_id": moveitem_res[0] ,"ServerId": moveitem_res[2]}, curs)
#        conn.commit()

if storage.close_conn_curs(conn):
        del conn, curs

#a = raw_input()
