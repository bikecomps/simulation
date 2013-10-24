import csv

# Static class for now. Doesn't really need to be I guess
class Analyzer:

    @staticmethod
    def read_file(file_name):
        trips = []
        with open(file_name, 'r') as f:
            reader = csv.reader(f)
            for line in reader:
                trips.append(*line)

        return trips

    @staticmethod
    def write_stats(results, file_name):
        print "Something would happen here"

    @staticmethod
    def analyze(trip_list):
        analyzed_data = []
        for trip in trip_list:
            csv_output = # Do something
            analyzed_data.append(csv_output)
        return analyzed_data
        

def main():
    trips = Analyzer.read_file("test.csv")
    stats = Analyzer.analyze(trips)
    Analyzer.write_stats(stats, "output.csv")

if __name__ == '__main__':
    main()
