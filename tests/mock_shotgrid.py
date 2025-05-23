from unittest.mock import MagicMock
from .mock_data import MOCK_DATA, MOCK_SCHEMA


class MockFlow:
    """
    A mock Flow class. Flow is used to set up and access a SG connection
    """

    def __init__(self) -> None:
        # Mock Flow's api functions
        self.api = MagicMock()
        self.api.find_one.side_effect = self.mock_find_one
        self.api.find.side_effect = self.mock_find
        self.api.create.side_effect = self.mock_create
        self.api.update.side_effect = self.mock_update
        self.api.delete.side_effect = self.mock_delete
        self.api.schema_read.return_value = MOCK_SCHEMA

        # Track created entities for testing (This is our pretend db)
        self.created_entities = {}
        self.next_id = 10000

    def mock_find_one(self, entity_type, filters, fields=None):
        """
        Mock SG find_one api call
        """

        # Find the ID in the filters
        entity_id = None
        for f in filters:
            if f[0] == 'id' and f[1] == 'is':
                entity_id = f[2]
                break

        if not entity_id:
            # We just have an entity ID to proceed
            return None

        if entity_type in MOCK_DATA and entity_id in MOCK_DATA[entity_type]:
            # We found the record in our original mock data
            result = MOCK_DATA[entity_type][entity_id].copy()
        elif (
            entity_type in self.created_entities and entity_id in self.created_entities[entity_type]
        ):
            # We found the record in our "database"
            result = self.created_entities[entity_type][entity_id]
        else:
            # We did not find the record at all, abort
            return None

        # Add the id to the result if needed
        if 'id' not in result:
            result['id'] = entity_id

        # Filter the results based on the required fields
        if fields and not isinstance(fields, list):
            # We passed a single field, but SG expects a list
            fields = [fields]
        if fields:
            # Fiulter
            filtered_result = {k: result[k] for k in fields if k in result}
            filtered_result['id'] = entity_id
            filtered_result['type'] = entity_type
            return filtered_result

        return result

    def mock_find(self, entity_type, filters, fields=None):
        """
        Mock SG find api call
        """
        if entity_type not in MOCK_DATA and entity_type not in self.created_entities:
            # We don't have this entity type in our mock data or created entities, abort
            return []

        results = []

        # First, collect all entities of this type from both mock data and created entities
        all_entities = {}

        # Add entities from mock data
        if entity_type in MOCK_DATA:
            for entity_id, entity_data in MOCK_DATA[entity_type].items():
                entity_copy = entity_data.copy()
                entity_copy['id'] = entity_id
                entity_copy['type'] = entity_type
                all_entities[entity_id] = entity_copy

        # Add entities from created entities
        if entity_type in self.created_entities:
            for entity_id, entity_data in self.created_entities[entity_type].items():
                entity_copy = entity_data.copy()
                entity_copy['id'] = entity_id
                entity_copy['type'] = entity_type
                all_entities[entity_id] = entity_copy

        # If no filters, return all entities
        if not filters:
            results = list(all_entities.values())
        else:
            # Apply filters
            filtered_ids = set(all_entities.keys())
            for filter_item in filters:
                field, operator, value = filter_item

                if operator == 'is' and field == 'id':
                    # Filter by ID
                    filtered_ids = {value} if value in all_entities else set()
                elif operator == 'in' and field == 'id':
                    # Filter by multiple IDs
                    filtered_ids = filtered_ids.intersection(set(value))
                elif operator == 'contains' and field in ['code', 'name', 'content']:
                    # Filter entities containing a string in their name/code/content
                    filtered_ids = {
                        entity_id
                        for entity_id in filtered_ids
                        if field in all_entities[entity_id]
                        and isinstance(all_entities[entity_id][field], str)
                        and value in all_entities[entity_id][field]
                    }
                elif operator == 'is' and field in ['code', 'name', 'content']:
                    # Filter entities with exact string in their name/code/content
                    filtered_ids = {
                        entity_id
                        for entity_id in filtered_ids
                        if field in all_entities[entity_id]
                        and all_entities[entity_id][field] == value
                    }

            # Collect results from filtered IDs
            results = [all_entities[entity_id] for entity_id in filtered_ids]

        # Apply field filtering if needed
        if fields:
            if not isinstance(fields, list):
                fields = [fields]

            filtered_results = []
            for result in results:
                filtered_result = {k: result[k] for k in fields if k in result}
                filtered_result['id'] = result['id']
                filtered_result['type'] = entity_type
                filtered_results.append(filtered_result)

            return filtered_results

        return results

    def mock_create(self, entity_type, data):
        """
        Mock SG create api call
        """

        # Grab an id
        entity_id = self.next_id
        self.next_id += 1

        # Store the entity in our "database". First create a type category
        if entity_type not in self.created_entities:
            self.created_entities[entity_type] = {}

        self.created_entities[entity_type][entity_id] = data.copy()

        # Return the entity with its new ID
        result = data.copy()
        result['id'] = entity_id

        return result

    def mock_update(self, entity_type, entity_id, data):
        """
        Mock SG update api call
        """

        if entity_type not in MOCK_DATA or entity_id not in MOCK_DATA[entity_type]:
            # The entity was not found in our original mock data
            if (
                entity_type in self.created_entities
                and entity_id in self.created_entities[entity_type]
            ):
                # The entity WAS found in our "database"
                self.created_entities[entity_type][entity_id].update(data)
                result = self.created_entities[entity_type][entity_id].copy()
                result['id'] = entity_id

                return result

            # entity was not found in original mock data or in the "database"
            return None

        # The entity was found in our original mock data
        MOCK_DATA[entity_type][entity_id].update(data)

        # Return the updated entity
        result = MOCK_DATA[entity_type][entity_id].copy()
        result['id'] = entity_id

        return result

    def mock_delete(self, entity_type, entity_id):
        """
        Mock SG delete api call
        """
        if entity_type in MOCK_DATA and entity_id in MOCK_DATA[entity_type]:
            del MOCK_DATA[entity_type][entity_id]
            return True
        elif (
            entity_type in self.created_entities and entity_id in self.created_entities[entity_type]
        ):
            del self.created_entities[entity_type][entity_id]
            return True
        return False
