mcap_suites = {
                "01_CM": {
                          "CE_BV_01_C": ["con_mcl", "con_dc"],
                          "CE_BV_02_C": ["send_data"],
                          "CE_BV_03_C": ["con_mcl", "send_data"],
                          "CE_BV_04_C": ["con_dc", "send_data"],
                          },
                "02_CM_DIS": {
                              "CM_DIS_01_C": ["close_mcl"],
                              "CM_DIS_02_C": [],
                              "CM_DIS_03_C": [],
                              "CM_DIS_04_C": ["close_mcl"],
                              "CM_DIS_05_C": []
                              },
                "03_CM_REC": {
                              "CM_REC_BV_01_C": ["send_data", "close_dc", "close_mcl", "con_mcl", "recon_dc", "send_data", "close_dc", "close_mcl"],
                              "CM_REC_BV_02_C": ["send_data", "send_data"],
                              "CM_REC_BV_03_C": ["send_data", "bt_down", "bt_up", "con_mcl", "recon_dc", "send_data"], # FIXME
                              "CM_REC_BV_04_C": ["send_data", "bt_down", "bt_up", "send_data"], # FIXME
                              "CM_REC_BV_05_C": ["send_data", "close_dc", "recon_dc"],
                              "CM_REC_BV_06_C": ["send_data", "send_data"]
                              },
                "04_CM_DEL": {
                              "CM_DEL_BV_01_C": ["del_dc"],
                              "CM_DEL_BV_02_C": [],
                              "CM_DEL_BV_03_C": ["del_all"],
                              "CM_DEL_BV_04_C": [],
                              },
                "05_CM_ABT": {
                              "CM_ABT_BV_01_C": ["con_mcl", "neg_dc", "abort_dc", "close_mcl"],
                              "CM_ABT_BV_02_C": [],
                              "CM_ABT_BV_03_C": [],
                              },
                "06_ERR": {
                           "ERR_BI_01C": [],
                           "ERR_BI_02C": ["con_dc"],
                           "ERR_BI_03C": [],
                           "ERR_BI_04C": ["con_dc"],
                           "ERR_BI_05C": [],
                           "ERR_BI_06C": ["con_dc"],
                           "ERR_BI_07C": [],
                           "ERR_BI_08C": ["con_dc"],
                           "ERR_BI_09C": [],
                           "ERR_BI_10C": [],
                           "ERR_BI_11C": ["con_dc"],
                           "ERR_BI_12C": ["con_dc"],
                           "ERR_BI_13C": [],
                           "ERR_BI_14C": [],
                           "ERR_BI_15C": ["con_dc"],
#                           "ERR_BI_16C": [], #TODO: How implement this test
                           "ERR_BI_17C": ["con_dc"],
                           "ERR_BI_18C": ["con_dc"],
                           "ERR_BI_19C": [],
                           "ERR_BI_20C": ["enable_csp", "csp_cap"],
                           },
                "07_INV": {
                           "INV_BI_01_C": ["con_dc"],
                           "INV_BI_02_C": ["con_dc"],
                           "INV_BI_03_C": ["con_mcl", "con_dc", "send_data", "close_dc", "close_mcl"],
                           "INV_BI_04_C": [],
                           "INV_BI_05_C": [],
                           "INV_BI_06_C": [],
                           "INV_BI_07_C": [],
                           },
                "08_CS_I": {
                            "CS_I_BV_01_I": ["enable_csp", "csp_cap", "csp_set"],
                            "CS_I_BV_02_I": ["enable_csp", "csp_cap", "csp_seti"],
                            "CS_I_BV_03_I": ["enable_csp", "csp_cap", "csp_set"],
                            "CS_I_BV_04_I": ["enable_csp", "csp_cap", "csp_set"],
                            },
                "09_CS_R": {
                            "CS_R_BV_01_I": ["enable_csp"],
                            "CS_R_BV_02_I": ["enable_csp"],
                            "CS_R_BV_03_I": ["enable_csp"],
                            "CS_R_BV_04_I": ["enable_csp", "send_data"],
                            },
                "10_CS_ERR": {
                              "CS_ERR_BI_01_C": ["enable_csp"], #TODO: Fix this test
                              "CS_ERR_BI_02_C": ["enable_csp"],
                              "CS_ERR_BI_03_C": ["enable_csp"],
                              "CS_ERR_BI_04_C": ["enable_csp"],
                              },
                "11_QUIT": {
                            "QUIT_01_C": ["exit"],
                            },
            }


class TestSuite:
    current_suite_index = 0
    current_suite = None
    current_test_commands = None
    current_command = None
    current_suite_index = 0
    current_suite_keys = []
    current_test_index = 0
    current_command_index = 0

    def __init__(self, suites):
        self.suites = suites
        self.suite_names_dict = suites.keys()
        self.suite_names_dict.sort()
        self.reposition_test()

    def reposition_test(self):
        self.current_suite = self.suites[self.suite_names_dict[self.current_suite_index]]

        self.current_suite_keys = self.current_suite.keys()
        self.current_suite_keys.sort()

        self.current_test_commands = self.current_suite[self.current_suite_keys[self.current_test_index]]
        if len(self.current_test_commands) > 0:
            self.current_command = self.current_test_commands[self.current_command_index]
        else:
            self.next_command()

    def get_current_command(self):
        return [self.current_command]

    def command_matching(self, token):
        suite_name = self.suite_names_dict[self.current_suite_index]
        test_name = self.current_suite_keys[self.current_test_index]
	print suite_name, test_name
	return token in suite_name or token in test_name

    def seek_command(self, token):
        saved_current_suite_index = self.current_suite_index
	saved_current_test_index = self.current_test_index
        saved_current_command_index = self.current_command_index

	while self.next_command():
            if self.command_matching(token):
                print "Found"
                return True

        self.current_suite_index = saved_current_suite_index
        self.current_test_index = saved_current_test_index
        self.current_command_index = saved_current_command_index
        self.reposition_test()
        print "Not found, reverting"
        return False

    def next_command(self):
        has_next_command = False

        while has_next_command == False:
            self.current_command_index += 1

            if self.current_command_index >= len(self.current_test_commands):
                self.current_test_index += 1
                self.current_command_index = 0
                if self.current_test_index >= len(self.current_suite_keys):
                    #Go to next suite
                    self.current_test_index = 0
                    self.current_suite_index += 1
                    if self.current_suite_index >= len(self.suite_names_dict):
                        return False

                    self.current_suite = self.suites[self.suite_names_dict[self.current_suite_index]]
                    self.current_suite_keys = self.current_suite.keys()
                    self.current_suite_keys.sort()

                self.current_test_commands = self.current_suite[self.current_suite_keys[self.current_test_index]]

                self.current_suite = self.suites[self.suite_names_dict[self.current_suite_index]]
                self.current_suite_keys = self.current_suite.keys()
                self.current_suite_keys.sort()

            if self.current_command_index < len(self.current_test_commands):
                has_next_command = True

        self.current_command = self.current_test_commands[self.current_command_index]
	return True


    def command_info(self):
        print '\n===> Suite: "%s", Test: "%s", Command: "%s"' % (
            self.suite_names_dict[self.current_suite_index][3:], self.current_suite_keys[self.current_test_index], self.current_command)
