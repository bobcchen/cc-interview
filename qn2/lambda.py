import boto3
import csv
import io
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

client = boto3.client('s3')

def lambda_handler(event, context):

    res_csvio = io.StringIO()
    res_writer = csv.writer(res_csvio)
    res_writer.writerow(['Restaurant id', 'Restaurant name', 'Country name', 'City name', 'User rating votes', 'User aggregate_rating', 'Cuisines'])
    
    event_csvio = io.StringIO()
    event_writer = csv.writer(event_csvio)
    event_writer.writerow(['Event id', 'Restaurant id', 'Restaurant name', 'Photo url', 'Event title', 'Event start date', 'Event end date'])

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
                res_writer.writerow(get_res_row(res_json, res_id))
                restaurant_count += 1
                
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
                            # logger.info("skipping event with id {} due to start date {} and end date {}...".format(event_id, event_start_date, event_end_date))
                            continue
                            
                        event_writer.writerow(get_event_row(event_json, event_id, res_id, res_name))
                        event_count += 1
    logger.info("end ingestion")
    logger.info("ingested {} restaurants and {} events".format(restaurant_count, event_count))

    res_response = client.put_object(Body=res_csvio.getvalue(), ContentType='text/csv', Bucket='cc-interview-bucket', Key='restaurants.csv')
    if res_response['ResponseMetadata']['HTTPStatusCode'] == 200:
        logger.info("successfully uploaded restaurants.csv to cc-interview-bucket")
    else:
        logger.error("failed to upload restaurants.csv")
    event_response = client.put_object(Body=event_csvio.getvalue(), ContentType='text/csv', Bucket='cc-interview-bucket', Key='events.csv')
    if event_response['ResponseMetadata']['HTTPStatusCode'] == 200:
        logger.info("successfully uploaded events.csv to cc-interview-bucket")
    else:
        logger.error("failed to upload events.csv")

    return "ingested {} restaurants and {} events".format(restaurant_count, event_count)

def get_res_row(res_json, res_id):
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

    res_name = get_field_value(res_json, 'name', ("restaurant", res_id))

    country_id = get_field_value(get_field_value(res_json, 'location', ("restaurant", res_id)), 'country_id', ("restaurant", res_id))
    if country_id in country_map:
        country_name = country_map[country_id]
    else:
        logger.warning("restaurant with id {} has invalid country code {}, using \"NA\" as country name...".format(res_id, country_id))
        country_name = "NA"

    city_name = get_field_value(get_field_value(res_json, 'location', ("restaurant", res_id)), 'city', ("restaurant", res_id))
    user_rating_votes = get_field_value(get_field_value(res_json, 'user_rating', ("restaurant", res_id)), 'votes', ("restaurant", res_id))
    user_aggregate_rating = get_field_value(get_field_value(res_json, 'user_rating', ("restaurant", res_id)), 'aggregate_rating', ("restaurant", res_id))
    cuisines = get_field_value(res_json, 'cuisines', ("restaurant", res_id))

    return [res_id, res_name, country_name, city_name, user_rating_votes, user_aggregate_rating, cuisines]

def get_event_row(event_json, event_id, res_id, res_name):

    urls = []
    for photo in event_json.get('photos',[]):
        url = get_field_value(get_field_value(photo, 'photo', ("event", event_id)), 'url', ("event", event_id))
        if not url == "NA":
            urls.append(url)

    if urls:
        photo_url = urls
    else:
        logger.info("event with id {} does not have photos, using \"NA\" as field value...".format(event_id))
        photo_url = "NA"

    event_title = get_field_value(event_json, 'title', ("event", event_id))
    event_start_date = get_field_value(event_json, 'start_date', ("event", event_id))
    event_end_date = get_field_value(event_json, 'end_date', ("event", event_id))

    return [event_id, res_id, res_name, photo_url, event_title, event_start_date, event_end_date]

def get_field_value(json, field, id):
    if type(json) is dict and field in json:
        return json[field]
    else:
        logger.warning("{} with id {} does not have {} field, using \"NA\" as field value...".format(id[0], id[1], field))
        return "NA"