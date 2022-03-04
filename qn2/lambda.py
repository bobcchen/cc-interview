import boto3
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

client = boto3.client('dynamodb')

def lambda_handler(event, context):
    
    restaurant_count = 0
    event_count = 0

    logger.info("start ingestion...")
    for response in event:
        if 'restaurants' in response:
            #for restaurants
            for restaurant in response.get('restaurants',[]):
                res_json = get_field_value(restaurant, 'restaurant', ("restaurant", "NA"))
                if type(res_json) is not dict:
                    logger.warning("skipped restaurant obj {} due to unexpected format...".format(restaurant))
                    continue
                if 'id' not in res_json:
                    logger.warning("skipped restaurant obj {} due to missing id...".format(res_json))
                    continue
                res_id = res_json['id']
                response = client.put_item(
                    TableName='restaurant-table',
                    Item = get_res_obj(res_json, res_id),
                    ReturnValues = 'ALL_OLD'
                )
                statusCode = response['ResponseMetadata']['HTTPStatusCode']
                if statusCode == 200:
                    if "Attributes" in response:
                        logger.warning("restaurant with id {} already exists, it is replaced with new object...".format(res_id))
                    else:
                        restaurant_count += 1
                        # logger.info("successfully ingested restaurant with id {}, ingested {} restaurants so far...".format(res_id, restaurant_count))
                else:
                    logger.error("error ingesting restaurant with id {}".format(res_id))
                
                #for events
                res_name = get_field_value(res_json, 'name', ("restaurant", res_id))
                if "zomato_events" in res_json:
                    for event in res_json.get('zomato_events',[]):
                        event_json = get_field_value(event, 'event', ("event", "NA"))
                        if type(event_json) is not dict:
                            logger.warning("skipped event obj {} due to unexpected format...".format(event))
                            continue
                        if 'event_id' not in event_json:
                            logger.warning("skipped event obj {} due to missing id...".format(event_json))
                            continue
                        event_id = str(event_json['event_id'])
                        event_start_date = get_field_value(event_json, 'start_date', ("event", event_id))
                        event_end_date = get_field_value(event_json, 'end_date', ("event", event_id))

                        #simple filter to check that both start and end dates are both in April 2017
                        if event_start_date == "NA" or event_end_date == "NA" or event_start_date < "2017-04-01" or event_end_date > "2017-04-30":
                            logger.info("skipping event with id {} due to start date {} and end date {}...".format(event_id, event_start_date, event_end_date))
                            continue
                            
                        response = client.put_item(
                            TableName='event-table',
                            Item = get_event_obj(event_json, event_id, res_id, res_name),
                            ReturnValues = 'ALL_OLD'
                        )
                        statusCode = response['ResponseMetadata']['HTTPStatusCode']
                        if statusCode == 200:
                            if "Attributes" in response:
                                logger.warning("event with id {} already exists, it is replaced with new object...".format(event_id))
                            else:
                                event_count += 1
                                # logger.info("successfully ingested event with id {}, ingested {} events so far...".format(event_id, event_count))
                        else:
                            logger.error("error ingesting event with id {}".format(event_id))
    logger.info("end ingestion")
    logger.info("ingested {} restaurants and {} events".format(restaurant_count, event_count))

    return "ingested {} restaurants and {} events".format(restaurant_count, event_count)

def get_res_obj(res_json, res_id):
    country_map = {
        1: "India",
        14: "Australia",
        30: "Brazil",
        37: "Canada",
        94: "Indonesia",
        148: "New Zealand",
        162: "Phillipines",
        166: "Qatar",
        184: "Singapore",
        189: "South Africa",
        191: "Sri Lanka",
        208: "Turkey",
        214: "UAE",
        215: "United Kingdom",
        216: "United States"
    }

    country_id = get_field_value(get_field_value(res_json, 'location', ("restaurant", res_id)), 'country_id', ("restaurant", res_id))
    if country_id in country_map:
        country_name = country_map[country_id]
    else:
        logger.warning("restaurant with id {} has invalid country code {}, using \"NA\" as country name...".format(res_id, country_id))
        country_name = "NA"

    user_rating_votes = get_field_value(get_field_value(res_json, 'user_rating', ("restaurant", res_id)), 'votes', ("restaurant", res_id))
    if user_rating_votes == "NA":
        user_rating_votes_obj = {
            'S': user_rating_votes
        }
    else:
        user_rating_votes_obj = {
            'N': str(user_rating_votes)
        }

    user_aggregate_rating = get_field_value(get_field_value(res_json, 'user_rating', ("restaurant", res_id)), 'aggregate_rating', ("restaurant", res_id))
    if user_aggregate_rating == "NA":
        user_aggregate_rating_obj = {
            'S': user_aggregate_rating
        }
    else:
        user_aggregate_rating_obj = {
            'N': str(user_aggregate_rating)
        }

    return {
        'Restaurant id': {
            'S': res_id
        },
        'Restaurant name': {
            'S': get_field_value(res_json, 'name', ("restaurant", res_id))
        },
        'Country name': {
            'S': country_name
        },
        'City name': {
            'S': get_field_value(get_field_value(res_json, 'location', ("restaurant", res_id)), 'city', ("restaurant", res_id))
        },
        'User rating votes': user_rating_votes_obj,
        'User aggregate_rating': user_aggregate_rating_obj,
        'Cuisines': {
            'S': get_field_value(res_json, 'cuisines', ("restaurant", res_id))
        }
    }

def get_event_obj(event_json, event_id, res_id, res_name):

    photo_urls = []
    for photo in event_json.get('photos',[]):
        url = get_field_value(get_field_value(photo, 'photo', ("event", event_id)), 'url', ("event", event_id))
        if not url == "NA":
            photo_urls.append(url)

    if photo_urls:
        photo_url_obj = {
            'SS': photo_urls
        }
    else:
        photo_url_obj = {
            'S': "NA"
        }

    return {
        'Event id': {
            'S': event_id
        },
        'Restaurant id': {
            'S': res_id
        },
        'Restaurant name': {
            'S': res_name
        },
        'Photo url': photo_url_obj,
        'Event title': {
            'S': get_field_value(event_json, 'title', ("event", event_id))
        },
        'Event start date': {
            'S': get_field_value(event_json, 'start_date', ("event", event_id))
        },
        'Event end date': {
            'S': get_field_value(event_json, 'end_date', ("event", event_id))
        }
    }

def get_field_value(json, field, id):
    if type(json) is dict and field in json:
        return json[field]
    else:
        logger.warning("{} with id {} does not have {} field, using \"NA\" as field value...".format(id[0], id[1], field))
        return "NA"