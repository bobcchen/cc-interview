import boto3
import csv
import io
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

client = boto3.client('s3')

def lambda_handler(event, context):

    csvio = io.StringIO()
    writer = csv.writer(csvio)
    writer.writerow(['rating_text', 'aggregate_rating'])

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
                writer.writerow(get_row(res_json, res_id))
    logger.info("end ingestion")

    response = client.put_object(Body=csvio.getvalue(), ContentType='text/csv', Bucket='cc-interview-bucket', Key='reviews.csv')
    return response

def get_row(res_json, res_id):
    rating_text = get_field_value(get_field_value(res_json, 'user_rating', ("restaurant", res_id)), 'rating_text', ("restaurant", res_id))
    user_aggregate_rating = get_field_value(get_field_value(res_json, 'user_rating', ("restaurant", res_id)), 'aggregate_rating', ("restaurant", res_id))

    return [rating_text, user_aggregate_rating]

def get_field_value(json, field, id):
    if type(json) is dict and field in json:
        return json[field]
    else:
        logger.warning("{} with id {} does not have {} field, using \"NA\" as field value...".format(id[0], id[1], field))
        return "NA"