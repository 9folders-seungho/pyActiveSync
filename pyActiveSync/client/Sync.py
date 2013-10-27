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

from utils.wapxml import wapxmltree, wapxmlnode

from objects.MSASEMAIL import Email, parse_email_to_dict

class Sync:
    """'Sync' command builders and parsers"""
    class sync_response_collection:
        def __init__(self):
            self.SyncKey = 0
            self.CollectionId = None
            self.Status = 0
            self.MoreAvailable = None
            self.Commands = []
            self.Responses = None

    @staticmethod
    def build(synckeys, collections):
        as_sync_xmldoc_req = wapxmltree()
        xml_as_sync_rootnode = wapxmlnode("Sync")
        as_sync_xmldoc_req.set_root(xml_as_sync_rootnode, "airsync")

        xml_as_collections_node = wapxmlnode("Collections", xml_as_sync_rootnode)

        for collection_id in collections.keys():
            xml_as_Collection_node = wapxmlnode("Collection", xml_as_collections_node)  #http://msdn.microsoft.com/en-us/library/gg650891(v=exchg.80).aspx
            try:
                xml_as_SyncKey_node = wapxmlnode("SyncKey", xml_as_Collection_node, synckeys[collection_id])    #http://msdn.microsoft.com/en-us/library/gg663426(v=exchg.80).aspx
            except KeyError:
                xml_as_SyncKey_node = wapxmlnode("SyncKey", xml_as_Collection_node, "0")
                
            xml_as_CollectionId_node = wapxmlnode("CollectionId", xml_as_Collection_node, collection_id) #http://msdn.microsoft.com/en-us/library/gg650886(v=exchg.80).aspx

            for parameter in collections[collection_id].keys():
                if parameter == "Options":
                    xml_as_Options_node = wapxmlnode(parameter, xml_as_Collection_node)
                    for option_parameter in collections[collection_id][parameter].keys():
                        if option_parameter.startswith("airsync"):
                            for airsyncpref_node in collections[collection_id][parameter][option_parameter]:
                                xml_as_Options_airsyncpref_node = wapxmlnode(option_parameter.replace("_",":"), xml_as_Options_node)
                                wapxmlnode("airsyncbase:Type", xml_as_Options_airsyncpref_node, airsyncpref_node["Type"])
                                del airsyncpref_node["Type"]
                                for airsyncpref_parameter in airsyncpref_node.keys():
                                    wapxmlnode("airsyncbase:%s" % airsyncpref_parameter, xml_as_Options_airsyncpref_node, airsyncpref_node[airsyncpref_parameter])
                        elif option_parameter.startswith("rm"):
                            wapxmlnode(option_parameter.replace("_",":"), xml_as_Options_node, collections[collection_id][parameter][option_parameter])
                        else:
                            wapxmlnode(option_parameter, xml_as_Options_node, collections[collection_id][parameter][option_parameter])
                else:
                    wapxmlnode(parameter, xml_as_Collection_node, collections[collection_id][parameter])
        return as_sync_xmldoc_req

    @staticmethod
    def parse_email_obj(message):   
        new_message = Email()
        new_message.parse(message)
        return new_message

    @staticmethod
    def parse_email_dict(message):
        return parse_email_to_dict(message)

    @staticmethod
    def parse(wapxml):

        namespace = "airsync"
        root_tag = "Sync"

        root_element = wapxml.get_root()
        if root_element.get_xmlns() != namespace:
            raise AttributeError("Xmlns '%s' submitted to '%s' parser. Should be '%s'." % (root_element.get_xmlns(), root_tag, namespace))
        if root_element.tag != root_tag:
            raise AttributeError("Root tag '%s' submitted to '%s' parser. Should be '%s'." % (root_element.tag, root_tag, root_tag))

        airsyncbase_sync_children = root_element.get_children()
        if len(airsyncbase_sync_children) >  1:
            raise AttributeError("%s response does not conform to any known %s responses." % (root_tag, root_tag))
        if airsyncbase_sync_children[0].tag == "Status":
            if airsyncbase_sync_children[0].text == "4":
                print "Sync Status: 4, Protocol Error."
        if airsyncbase_sync_children[0].tag != "Collections":
            raise AttributeError("%s response does not conform to any known %s responses." % (root_tag, root_tag))

        response = []            

        airsyncbase_sync_collections_children = airsyncbase_sync_children[0].get_children()
        airsyncbase_sync_collections_children_count = len(airsyncbase_sync_collections_children)
        collections_counter = 0
        while collections_counter < airsyncbase_sync_collections_children_count:

            if airsyncbase_sync_collections_children[collections_counter].tag != "Collection":
                raise AttributeError("Sync response does not conform to any known Sync responses.")

            airsyncbase_sync_collection_children = airsyncbase_sync_collections_children[collections_counter].get_children()
            airsyncbase_sync_collection_children_count = len(airsyncbase_sync_collection_children)
            collection_counter = 0
            new_collection = Sync.sync_response_collection()
            while collection_counter < airsyncbase_sync_collection_children_count:
                if airsyncbase_sync_collection_children[collection_counter].tag == "SyncKey":
                    new_collection.SyncKey = airsyncbase_sync_collection_children[collection_counter].text
                elif airsyncbase_sync_collection_children[collection_counter].tag == "CollectionId":
                    new_collection.CollectionId = airsyncbase_sync_collection_children[collection_counter].text
                elif airsyncbase_sync_collection_children[collection_counter].tag == "Status":
                    new_collection.Status = airsyncbase_sync_collection_children[collection_counter].text
                    if new_collection.Status != "1":
                        response.append(new_collection)
                elif airsyncbase_sync_collection_children[collection_counter].tag == "MoreAvailable":
                    new_collection.MoreAvailable = airsyncbase_sync_collection_children[collection_counter].text
                elif airsyncbase_sync_collection_children[collection_counter].tag == "Commands":
                    airsyncbase_sync_commands_children = airsyncbase_sync_collection_children[collection_counter].get_children()
                    airsyncbase_sync_commands_children_count = len(airsyncbase_sync_commands_children)
                    commands_counter = 0
                    while commands_counter < airsyncbase_sync_commands_children_count:
                        if airsyncbase_sync_commands_children[commands_counter].tag == "Add":
                            add_message = Sync.parse_email_dict(airsyncbase_sync_commands_children[commands_counter])
                            new_collection.Commands.append(("Add", add_message))
                        elif airsyncbase_sync_commands_children[commands_counter].tag == "Delete":
                            new_collection.Commands.append(("Delete", airsyncbase_sync_commands_children[commands_counter].get_children()[0].text))
                        elif airsyncbase_sync_commands_children[commands_counter].tag == "Change":
                            update_message = Sync.parse_email_dict(airsyncbase_sync_commands_children[commands_counter])
                            new_collection.Commands.append(("Change", update_message))
                        elif airsyncbase_sync_commands_children[commands_counter].tag == "SoftDelete":
                            new_collection.Commands.append(("SoftDelete", airsyncbase_sync_commands_children[commands_counter].get_children()[0].text))
                        commands_counter+=1
                elif airsyncbase_sync_collection_children[collection_counter].tag == "Responses":
                    print airsyncbase_sync_collection_children[collection_counter]
                collection_counter+=1
            response.append(new_collection)
            collections_counter+=1
        return response
