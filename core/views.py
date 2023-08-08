from django.shortcuts import render
from django.http import JsonResponse
import requests, json, csv, time, os, random
from flatten_json import flatten
from urllib.parse import urlparse, parse_qs, unquote
from django.http import FileResponse
from django.core.mail import EmailMessage
from django.conf import settings
import stripe
from django.core.mail import EmailMultiAlternatives



stripe.api_key = "sk_test_51MMFduGpCeSCCFeRbljK0jUnebPuiswBX7rWBNvLBOZ6MMRwCzWXoQeSkH3iFm7fILNrjLyhkLbUZrKDSlgOaduS00f3rf8Wrt"
random_integer = str(random.randint(999999, 9999999)) + '' + str(random.randint(999, 9999))
# Create your views here.
def Index(request):
    if request.method == 'POST':
        url = request.POST.get('url')
        email = request.POST.get('email')
        name = request.POST.get("name")
        needed_data = int(request.POST.get('leads')) * 1000
        total_bill = int(float(request.POST.get('total_bill').replace('$', ''))) * 100
        if total_bill < 50:
            return JsonResponse({"error": "Total bill must be at least $0.50 USD."}, status=400)

        csv_file_path = get_people_data(url, needed_data)

        if not is_csv_file_valid(csv_file_path):
            return JsonResponse({"error": "No data available in CSV file."}, status=500)


        charge_status = create_stripe_charge(total_bill, email)
        if charge_status == "succeeded":
            download_url = "https://findylead.com/media/data/" + random_integer + '.csv'
            send_data_email(email, csv_file_path, download_url, url, name, needed_data)
            return FileResponse(open(csv_file_path, 'rb'), as_attachment=True)
        else:
            return JsonResponse({"error": "Stripe charge failed. Please try again."}, status=500)

    return render(request, 'home.html')


def is_csv_file_valid(file_path):
    with open(file_path, 'r', newline='', encoding='utf-8') as csv_file:
        reader = csv.reader(csv_file)
        header = next(reader, None)
        for row in reader:
            if any(row):
                return True
        return False

def create_stripe_charge(amount, email):
    try:
        charge = stripe.Charge.create(
            amount=amount,
            currency="usd",
            source="tok_visa",
            description="Apollo Scrapper Charge",
            receipt_email=email,
        )
        return charge.status
    except stripe.error.StripeError as e:
        return str(e)

def get_field(person, field):
    return person.get(field, '')

def get_people_data(url, needed_data):
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query, keep_blank_values=True)
    fragment_params = {}
    if parsed_url.fragment:
        for item in parsed_url.fragment.split('&'):
            key_value = item.split('=')
            if len(key_value) == 2:
                key, value = key_value
                key = unquote(key).rstrip('[]')
                value = unquote(value)
                if key in fragment_params:
                    fragment_params[key].append(value)
                else:
                    fragment_params[key] = [value]

    api_key = "Fcad7I_Iy846Abij-F9ghg"
    payload = {
        "api_key": api_key,
        "per_page": 100,
    }
    for key, values in query_params.items():
        key = unquote(key).rstrip('[]')
        values = [unquote(value) for value in values]
        key = ''.join(['_' + c.lower() if c.isupper() else c for c in key])
        payload[key] = values

    for key, values in fragment_params.items():
        key = ''.join(['_' + c.lower() if c.isupper() else c for c in key])
        payload[key] = values

    source = "https://api.apollo.io/v1/mixed_people/search"
    csv_file = random_integer + '.csv'
    
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache"
    }

    all_people = []
    data_count = 0
    payload['page'] = 1

    while data_count < 100:
        time.sleep(1)
        try:
            response = requests.post(source, data=json.dumps(payload), headers=headers)
            response.raise_for_status()

            response_data = response.json()
            retrieved_people = response_data['people']

            print(f"Retrieved {len(retrieved_people)} data from page {payload['page']}")
            all_people.extend(retrieved_people)
            data_count += len(retrieved_people)
            payload['page'] += 1

            if len(retrieved_people) == 0:
                print("No more data available.")
                break

        except requests.RequestException as e:
            print(f"Error: {e}")
            break


    data_folder = os.path.join(settings.MEDIA_ROOT, 'data')
    os.makedirs(data_folder, exist_ok=True)

    fields = [
        'id', 'email', 'first_name', 'last_name', 'name', 'linkedin_url', 'title',
        'headline', 'city', 'state', 'country', 'org_number', 'org_founded_year',
        'organization_logo', 'organization_domain', 'phone_number',
        'organization_id', 'organization_name', 'organization_website_url',
        'input_filters'

        # 'id', 'email', 'first_name', 'last_name', 'name', 'linkedin_url',	'twitter_url',	'facebook_url',	
        # 'city', 'state', 'country',	'Organization Id',	'organization_name',	'organization_website_url'	,
        # 'organization_primary_phone_number'	,'departments_0'	,'organization_founded_year',	'organization_logo_url'	,'organization_website_url',
        # 	'organization_facebook_url'	,'organization_angellist_url',	'organization_primary_domain'	,'organization_linkedin_url',	'organization_twitter_url'
    ]

    flattened_people = [flatten(person) for person in all_people]

    field_names = [field.replace('_', ' ').title() for field in fields]

    csv_file_path = os.path.join(data_folder, csv_file)

    with open(csv_file_path, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(field_names)

        for person in flattened_people:
            row = [get_field(person, field) for field in fields]
            writer.writerow(row)

    return csv_file_path


def send_data_email(email, file, download_url, apollo_search_url, name, needed_data):
    subject = 'Your lead is ready to download 😎'
    
    # Plain text message with new lines using \n
    message_plain = f'''Hey {name}, Your {needed_data/1000}k leads are ready to download.
    Click the links below:

    Click here to download leads 🚀: {download_url}

    Click here to see the Apollo Search URL😎: {apollo_search_url}

    ----
    Arafat'''

    # HTML-formatted message with new lines using HTML tags
    message_html = f'''<p>Hey {name}, Your {needed_data/1000}k leads are ready to download.</p>
    <p>Click here to <a href="{download_url}">Download leads 🚀</a></p>

    <p>Click here to see the <a href="{apollo_search_url}">Apollo Search URL😎</a></p>

    <p>----</p>
    <p>Arafat</p>'''

    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [email]

    email_message = EmailMultiAlternatives(subject, message_plain, from_email, recipient_list)
    email_message.attach_alternative(message_html, 'text/html')
    email_message.attach_file(file)

    try:
        email_message.send()
        print('Email sent successfully')
    except Exception as e:
        print(f'Error sending email: {str(e)}')


def Success(request):
    return render(request, 'success.html')

