#!/usr/bin/python3

import argparse
import json
import os
import sys

from routes18xx.find_best_routes import find_best_routes_from_files

TEST_DIR = os.path.dirname(__file__)
TEST_DATA_ROOT_DIR = os.path.join(TEST_DIR, "data")

def _load_test_suite(suite_filepath):
    with open(suite_filepath) as suite_file:
        return json.load(suite_file)["tests"]

def _run_tests(suite_filename):
    expectations = _load_test_suite(suite_filename)

    passed = True
    for game, game_test_data in expectations.items():
        for test_data in game_test_data:
            print(f"{game} - {test_data['name']}")
            board_state_filename = os.path.join(TEST_DATA_ROOT_DIR, game, test_data["board-state"])
            railroads_filename = os.path.join(TEST_DATA_ROOT_DIR, game, test_data["railroads"])
            private_companies_filename = test_data.get("private-companies")
            if private_companies_filename:
                private_companies_filename = os.path.join(TEST_DATA_ROOT_DIR, game, private_companies_filename)
            failed_tests = []
            for active_name, expected_value in test_data["active"].items():
                best_route_set = find_best_routes_from_files(game, active_name,
                        board_state_filename, railroads_filename, private_companies_filename)
                if expected_value != best_route_set.value:
                    print(f"{active_name}: FAIL - expected: {expected_value}. actual: {best_route_set.value}")
                    failed_tests.append(active_name)
            if failed_tests:
                print(f"{game} - {test_data['name']}: FAILED - {', '.join(failed_tests)}")
                passed = False
            else:
                print("PASS")

            print("")

    return passed

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("suite_filename")

    return vars(parser.parse_args())

if __name__ == "__main__":
    args = parse_args()

    sys.exit(0 if _run_tests(args["suite_filename"]) else 1)