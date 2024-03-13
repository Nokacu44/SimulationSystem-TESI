import csv
import io
import zipfile
import shutil
from io import TextIOWrapper

def validate_gtfs(gtfs_source: str, output_dest: str):
    try:
        new_source = shutil.copy(gtfs_source, output_dest)
        with zipfile.ZipFile(new_source, 'a') as gtfs_file:
            file_list = gtfs_file.namelist()
            # TODO: valida la presenza di almeno i file necessari tra cui anche calendar.txt e calendar_dates.txt
            if "calendar.txt" not in file_list:
                if "calendar_dates.txt" in file_list:
                    calendar_data = _calendar_from_dates(zip_file=gtfs_file)
                    calendar_file = _generate_calendar_file(data=calendar_data)
                    gtfs_file.writestr('calendar.txt', calendar_file)
        return new_source
    except shutil.SameFileError:
        print("trying copy to same destination!")


def _calendar_from_dates(zip_file):
    calendar = {}
    with zip_file.open("calendar_dates.txt", 'r') as csv_file:
        text_file = TextIOWrapper(csv_file, encoding='utf-8')
        reader = csv.DictReader(text_file)
        for row in reader:
            service_id = row['service_id']
            date = row['date']
            exception_type = row['exception_type']

            if service_id not in calendar:
                calendar[service_id] = {'start_date': date, 'end_date': date, 'days': []}
            else:
                if date < calendar[service_id]['start_date']:
                    calendar[service_id]['start_date'] = date
                if date > calendar[service_id]['end_date']:
                    calendar[service_id]['end_date'] = date

            if exception_type == '1':
                calendar[service_id]['days'].append(date)
            elif exception_type == '2':
                if date in calendar[service_id]['days']:
                    calendar[service_id]['days'].remove(date)
    return calendar


def _generate_calendar_file(data) -> str:
    csv_buffer = io.StringIO()
    fieldnames = ['service_id', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
                  'start_date', 'end_date']
    writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
    writer.writeheader()

    for service_id, data in data.items():
        days = ['0'] * 7
        for day in data['days']:
            weekday = str((int(day) % 7) + 1)
            days[int(weekday) - 1] = '1'

        writer.writerow({
            'service_id': service_id,
            'monday': days[0],
            'tuesday': days[1],
            'wednesday': days[2],
            'thursday': days[3],
            'friday': days[4],
            'saturday': days[5],
            'sunday': days[6],
            'start_date': data['start_date'],
            'end_date': data['end_date']
        })

    return csv_buffer.getvalue()
