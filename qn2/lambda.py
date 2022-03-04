import boto3

client = boto3.client('dynamodb')

def lambda_handler(event, context):
    
    restaurant_count = 0
    event_count = 0

    for response in event:
        if 'restaurants' in response:
            for restaurant in response['restaurants']:
                res_json = restaurant['restaurant']
                res_id = res_json['id']
                res_name = res_json['name']
                response = client.put_item(
                    TableName='restaurant-table',
                    Item = get_res_obj(res_json),
                    ReturnValues = 'ALL_OLD'
                )
                statusCode = response['ResponseMetadata']['HTTPStatusCode']
                if statusCode == 200:
                    if "Attributes" in response:
                        print("restaurant with id {} already exists, it is replaced with new object...".format(res_id))
                    else:
                        restaurant_count += 1
                else:
                    print("error ingesting restaurant with id {}".format(res_id))
                
                if "zomato_events" in res_json:
                    for event in res_json['zomato_events']:
                        event_json = event['event']

                        #simple filter to check that both start and end dates are both in April 2017
                        if event_json['start_date'] >= "2017-04-01" and event_json['end_date'] <= "2017-04-30":
                            event_id = event_json['event_id']
                            response = client.put_item(
                                TableName='event-table',
                                Item = get_event_obj(event_json, res_id, res_name),
                                ReturnValues = 'ALL_OLD'
                            )
                            statusCode = response['ResponseMetadata']['HTTPStatusCode']
                            if statusCode == 200:
                                if "Attributes" in response:
                                    print("event with id {} already exists, it is replaced with new object...".format(event_id))
                                else:
                                    event_count += 1
                            else:
                                print("error ingesting event with id {}".format(event_id))
    
    return "ingested {} restaurants and {} events".format(restaurant_count, event_count)

def get_res_obj(res_json):
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

    return {
        'Restaurant id': {
            'S': res_json['id']
        },
        'Restaurant name': {
            'S': res_json['name']
        },
        'Country name': {
            'S': country_map[res_json['location']['country_id']]
        },
        'City name': {
            'S': res_json['location']['city']
        },
        'User rating votes': {
            'N': res_json['user_rating']['votes']
        },
        'User aggregate_rating': {
            'N': res_json['user_rating']['aggregate_rating']
        },
        'Cuisines': {
            'S': res_json['cuisines']
        }
    }

def get_event_obj(event_json, res_id, res_name):

    photo_urls = []
    for photo in event_json['photos']:
        photo_urls.append(photo['photo']['url'])

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
            'S': str(event_json['event_id'])
        },
        'Restaurant id': {
            'S': res_id
        },
        'Restaurant name': {
            'S': res_name
        },
        'Photo url': photo_url_obj,
        'Event title': {
            'S': event_json['title']
        },
        'Event start date': {
            'S': event_json['start_date']
        },
        'Event end date': {
            'S': event_json['end_date']
        }
    }