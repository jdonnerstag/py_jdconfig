""" PIL Engine config file """
# ----------------------------------------------------------------------------
# PIL Engine config file
# ----------------------------------------------------------------------------

import os
from datetime import datetime


# TODO: Keep for now as example, even though we are no longer using an RDBMS like Oracle
# Note: we don't want to load the creditionals and store them in our config.
# People may accidentially print it, put it into git, whatever. We rather want to lazily
# determine it when needed.
def PIL_DB_USER():
    return os.getenv("PIL_DB_USER", "dxcadmin")

def PIL_DB_PASS():
    return os.getenv("PIL_DB_PASS", "dxc-admin")

def CENT(fname):
    return {
        "full": "{data_files_input_dir}/" + f"ANO_DWH..DWH_TO_PIL_CENT_{fname}_(VTAG|FULL).*.A901",
        "delta": "{data_files_input_dir}/" + f"ANO_DWH..DWH_TO_PIL_CENT_{fname}_DELTA.*.A901",
    }

# This one can remain static
PIL_DB_NAME = os.getenv("PIL_DB_NAME", "pil-engine.cbn8qirdlx7k.us-east-1.rds.amazonaws.com:1521/orcl")

PROJECT_ROOT = "C:\\source_code\\COMSAFE"

# Don#t change the name "CONFIG". We expect the configs to be in their
CONFIG = {
    "version": 1,

    # The env variable for the environment specific config items. E.g. if PIL_CFG = "dev",
    # then use config-dev.py to replace specific values in config.py. Very much like "-c" cmdline
    # option, PIL_CFG can also be a filename or directory.
    # If not configured, "PIL_CFG" is the system default name
    # Note: considering the config load process, it's alwways the system default value that will be applied.
    "config_env_key": "PIL_CFG",

    # Number of processes used to load multiple files
    # Use a negative number to dynamically determine the pool size based on server
    # CPU, core and threads sizes. E.g. -1 => leave 1 core to the OS
    # TODO: Keep for now as example, even though we are not using it right now.
    "process_pool": -1,

    # TODO: Keep for now as example, even though we are not using it right now.
    "db": {
        # Lazy load the connection string. The actuall value will never be stored in config (not even in memory)
        "connection_string": lambda: f"{PIL_DB_USER()}/{PIL_DB_PASS()}@{PIL_DB_NAME}",
        "db_job_name": "PIL_IMPORT_FILES",

        # DB INSERT batch size
        "batch_size": 1_000,

        "schematas": {
            "pil_engine": PIL_DB_USER(),
            "pil_maintenance": "xxx",
            "pil_e2e": "xxx",
        },
    },

    # TODO: I don't think any of them is still valid
    "debug": {
        "log_progress_after": 20_000,
        "DISABLED stop_after": 100_000,
        "enable_reconciliation": False,
        "new_reconciliation": True,
    },

    # Define once, and re-use further down
    "log_dir": "/temp/logs",
    # This way we make it available in derived environment configs
    "project_root": PROJECT_ROOT,
    # Timestamp when the app was started
    "timestamp": lambda: datetime.now().strftime("%Y%m%d-%H%M%S"),

    "git": {
        "git_exe": "C:\\Program Files\\Git\\cmd\\git.exe",
        # TODO Move the remaining into a separate group
        "manual_files_git_repo": f"{PROJECT_ROOT}\\PIL-manual-files",
        # "temp_dir": "",
        "pull_all_script": ".\\bin\\scripts\\git_pull_all.ps1",
    },

    "file_configs": {
        "git_repo": f"{PROJECT_ROOT}\\PIL-config-2",
        # If "", then use 'config_env_key'
        # if None, then don't checkout branch
        "branch": None,     # "master",
        "pull_on_init": False,  # True,
        "directory": "file_config"
    },

    # TODO: I don't think we are using it still
    "file_sort": {
        "mem_size": 1_000_000_000,  # 1 GB
        "cmd": "gsort",     # Gow on windows
    },

    # Defaults. Might be overriden by specific file configs
    "files": {
        # Can be overriden in the file config
        "default_encoding": "iso_8859_1",

        # Default Root-Directory for output data
        # See pil_flow.py -d command line option
        "PIL_DATA": f"{PROJECT_ROOT}\\PIL-data-2",

        # The log file containing the details of a specific file import
        # Note that this config requires user provided values, not included in the config
        # Note: timestamp hsa been defined as lambda function and hence the return value is dyanmic
        "log_file": "{log_dir}/{filename}.{timestamp}.log",

        # If not provided via the commandline
        "input_files": "c:\\temp\\PIL\\anon_test_data\\*.gz",

        # The directory where sorted input files (VTAG, FULL, DELTA) are searched for by default
        "input_files_sorted": f"{PROJECT_ROOT}\\VF-data\\12_sorted",

        # The directory where FULL files are written to, after applying DELTA files
        "delta_files_applied": f"{PROJECT_ROOT}\\VF-data\\15_deltas_applied",

        "com_periods": f"{PROJECT_ROOT}\\VF-data\\16_com_periods",

        "step1_output": f"{PROJECT_ROOT}\\PIL-data-2\\11_input_reviewed",

        # The file where errornous records will be appended
        "failed_records": "{log_dir}/{filename}.{timestamp}.failed",

        # The file where filtered records will be appended
        "filtered_records": "{log_dir}/{filename}.{timestamp}.filtered",

        # Rename or move the file before processing
        "rename_when_processing": None,     # "{filedir}/{filename}.{timestamp}.processing",

        # Rename or move the file after processing
        "rename_when_finished": None,  # "{filedir}/{filename}.{timestamp}.done",

        # Events that are filtered during pipeline processing
        "event_filtered": "{log_dir}/events_filtered.{timestamp}.log",

        # Permanent FN license database file
        "FN-license-db": "{embedded-db.path}/FN-licenses.pickle",

        "MICOS-DB-File": "{embedded-db.path}/MICOS-DB-File.pickle",
    },

    # Files provided by users e.g. via a git repo
    "manual_files": {
        "category-classifiers": "{git.manual_files_git_repo}/Department/All/ALLENT_REF_CATEGORISECLASSIFIERS.xlsx",
        "SRNA-pricelist": "{git.manual_files_git_repo}/Department/All/ALLENT_REF_SRNAPRICES.xlsx",
        "product-catalog": "{git.manual_files_git_repo}/Department/All/**/Product-Catalog.xlsx",
        "channel-classification": "{git.manual_files_git_repo}/Department/All/ALLENT_REF_CHANNELCLASSIFICATION.xlsx",
        "multi-dimensional-config-data": "{git.manual_files_git_repo}/Department/All/ALLENT_REF_COMLOOKUPDATA.py",
        "system-config": "{git.manual_files_git_repo}/Department/All/ALLENT_REF_PILSYSTEMCONFIG.xlsx",
        "CENT-manual_adjustments": "{git.manual_files_git_repo}/Department/All/ALLENT_REF_MANUALSH.xlsx",
        "reason-code-pay": "{git.manual_files_git_repo}/Department/All/ALLENT_REF_REASONCODEPAY.xlsx",
        "manual-file-with-date": "{git.manual_files_git_repo}/Department/All/**/file_123.xlsx",
        "direct-sh-titles": "{git.manual_files_git_repo}/Department/Direct/**/DIRENT_REF_SHTITLES.xlsx",
        "VTS-rev-event-whitelist": "{git.manual_files_git_repo}/Department/All/**/VTS-revenue-event-whitelist.xlsx",
        "FN-license-price-info": "{git.manual_files_git_repo}/Department/All/**/FN-provision-info.xlsx",
        "multi-dim-example": "{git.manual_files_git_repo}/Department/All/example-multi-dimensional-data.xlsx",
    },

    # Data-files provided in S3 buckets, via SFTP, or similar. They are potentially large.
    "data_files_input_dir": f"{PROJECT_ROOT}/PIL-data-2/11_input_crlf_fixed",
    "data_files": {
        "assignment-full": [
            "{data_files_input_dir}/ANO_DWH..DWH_TO_PIL_ASSIGNMENT_VTAG.*.A901",
            "{data_files_input_dir}/ANO_DWH..DWH_TO_PIL_ASSIGNMENT_FULL.*.A901",
        ],
        "assignment-delta": [
            "{data_files_input_dir}/ANO_DWH..DWH_TO_PIL_ASSIGNMENT_DELTA.*.A901",
        ],

        "CENT": {
            "customer_account": CENT("CUSTOMER_ACCOUNT"),
            "named_account_assign": CENT("NAMED_ACCOUNT_ASSIGN"),
            "party": CENT("PARTY"),
            "sales_assignment": CENT("SALES_ASSIGNMENT"),
            "SL_main_resp": CENT("SL_MAIN_RESP"),
        },
    },

    # The list of reference data files that must be loaded before event processing
    "pil_input_files": "{git.manual_files_git_repo}/input_files.xlsx",

    # TODO: I don't think we are using it still
    "embedded-db": {
        "path": "./local_db",
    },

    "pipeline-directory": "{file_configs.git_repo}/workflows",

    "commission_nodes": {
        # Here we expect to find the actual python modules which implement Commission-Nodes.
        "modules": [
            "{file_configs.git_repo}/commission_nodes",
        ],
        # Here we expect to find the commission hierachy information
        "node_structure": [
            "{git.manual_files_git_repo}/Department/ALL/Commission-Hierarchy.xlsx",
            "{git.manual_files_git_repo}/Department/Direct/Commission-Hierarchy.xlsx",
            "{git.manual_files_git_repo}/Department/Indirect/Commission-Hierarchy.xlsx",
        ],
    },

    # TODO: Not yet implemented
    "pipelines": {
        "Review Input": {
            "task": "pil.tasks.ReviewInputTask",
            "depends_on": None,
            "config": {
                "files": "{root_dir}/{args.files}",
                "outdir": "{root_dir}/11_input_reviewed",
            }
        },

        "Sort Input": {
            "task": "xxx",
            "files": "{root_dir}/11_input_reviewed",
            "outdir": "{root_dir}/12_input_sorted",
            "memsize": 500_000_000,
            "depends_on": ["Review Input"],
        },

        "SFoBI to Dremio": {
            "task": "xxx",
            "files": "{root_dir}/12_input_sorted",
            "outdir": "{root_dir}/15_dremio",
            "commissionPeriod": "{args.commissionPeriod}",
            "effectiveDate": "{args.effectiveDate}",
            "depends_on": ["Sort Input"],
        },

        "Filter Dummy-Subscriber IDs": {
            "task": "xxx",
            "files": "{root_dir}/12_input_sorted",
            "outdir": "{root_dir}/15_dremio",
            "timeA": "{args.timeA}",
            "depends_on": ["SFoBI to Dremio"],
        },

        "Filter license events": {
            "task": "pil.tasks.FilterLicenseEventTask",
            "files": "{root_dir}/12_input_sorted",
            "outdir": "{root_dir}/15_dremio",
            "depends_on": ["Filter Dummy-Subscriber IDs"],
        },

        "SFoBI Commission Period ref-data": {
            "task": "pil.tasks.SFoBIComPeriodRefDataTask",
            "depends_on": ["Filter license events"],
            "config": {
                "files": "{root_dir}/12_input_sorted",
                "outdir": "{root_dir}/30_com_periods",
                "commissionPeriod": "{args.commissionPeriod}",
                "effectiveDate": "{args.effectiveDate}",
            },
        },

        "Get manual-files from git-repo": {
            "outdir": "{root_dir}/30_com_periods",
            "commissionPeriod": "{args.commissionPeriod}",
            "effectiveDate": "{args.effectiveDate}",
            "noPull": "{args.noPull}",
            "gitBranch": "{args.gitBranch or 'heads/DEV-1'}",
            "task": "pil.tasks.ManualFilesForComPeriodTask",
        },

        "Manual files to CSV": {
            "files": "{root_dir}/30_com_periods/{com_period}/manual-files/**/*.xlsx",
            "outdir": "{root_dir}/30_com_periods/{com_period}",
            "commissionPeriod": "{args.commissionPeriod}",
            "effectiveDate": "{args.effectiveDate}",
            "task": "pil.tasks.ManualFileToCsvTask",
            "depends_on": "Get manual-files from git-repo",
        },

        "Test Ref-Data in Commission Period folder": {
            "rootdir": "{root_dir}",
            "commissionPeriod": "{args.commissionPeriod}",
            "effectiveDate": "{args.effectiveDate}",
            "task": "pil.tasks.ComPeriodRefDataTestTask",
            "depends_on": ["Manual files to CSV"],
        },

        "Events for Commission Period": {
            "files": "{root_dir}/12_input_sorted",
            "outdir": "{root_dir}/30_com_periods",
            "commissionPeriod": "{args.commissionPeriod}",
            "effectiveDate": "{args.effectiveDate}",
            "dummySubscriptionFile": "{root_dir}/15_dremio/MICOS_CONTRACTS_DUMMY_SUBS/**/*.csv",
            "task": "pil.tasks.EventsForComPeriodTask",
            "depends_on": "Test Ref-Data in Commission Period folder",
        },

        "Auto-generate lic-events for com-period": {
            "files": "{root_dir}/12_input_sorted",
            "outdir": "{root_dir}/30_com_periods",
            "commissionPeriod": "{args.commissionPeriod}",
            "effectiveDate": "{args.effectiveDate}",
            "dummySubscriptionFile": "{root_dir}/15_dremio/MICOS_CONTRACTS_DUMMY_SUBS/**/*.csv",
            "task": "pil.tasks.AutogenerateLicenseEventsForComPeriodTask",
            "depends_on": "Events for Commission Period",
        },

        "Auto-generate activation events for com-period": {
            "files": "{root_dir}/12_input_sorted",
            "outdir": "{root_dir}/30_com_periods",
            "commissionPeriod": "{args.commissionPeriod}",
            "effectiveDate": "{args.effectiveDate}",
            "dummySubscriptionFile": "{root_dir}/15_dremio/MICOS_CONTRACTS_DUMMY_SUBS/**/*.csv",
            "task": "pil.tasks.AutogenerateActivationEventsForComPeriodTask",
            "depends_on": "Auto-generate lic-events for com-period",
        },

        "Ingest Tests": {
            "rootdir": "{root_dir}",
            "commissionPeriod": "{args.commissionPeriod}",
            "effectiveDate": "{args.effectiveDate}",
            "task": "pil.tasks.IngestTestTask",
            "depends_on": ["Auto-generate activation events for com-period"],
        },

        "CSV to Parquet": {
            "files": "{root_dir}/15_dremio",
            "outdir": "{root_dir}/16_parquet",
            "task": "pil.tasks.CsvToParquetTask",
            "depends_on": [],
        },
    },

    "logging": {
        "version": 1,
        "disable_existing_loggers": False,

        "formatters": {
            "simple": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "vf_format": """
Timestamp   M   YYYY-MM-DD HH:MM:SS
System
    M   Text    System name on which the event occurred
    List of Values are {COMSAFE_PIL Engine Core, COMSAFE_PIL Engine DB} COMSAFE_PIL Engine Core
Process M   Text    The process name which generated this log. Typically a collector name or DB procedure.
    List of values are {Collector, DB Procedure}    Collector
Error Code
    M   Text    A unique error code to identify the problem.    List of values are configured in DB table CMN_ERRORCD.
Severity
    M   Text    The level of the error classification.
    List of values are {Error, Warning, Debug, Info,  Unknown}
Description
    O   Text    A description of the error event with a message that corresponds to the error code.         Invalid File received from SFoBI for CENT
Comment O   Text    Any comment the application may like to provide to the analysis team to debug the issue Free Text   Error Raised from IMP_CE_ASGN Collector.

Individual fields in a single error message is separated by (;). Each messages are separated by a new line operator.
COMSAFE_PIL Engine will support two levels for log creation and the below table shows the log levels and the corresponding
severity levels of logs that will be generated in the log files.
An example log record will look like below:
2017-08-24 17:58:40,623;COMSAFE_PIL Engine Core;Technical;IMPORT;Collector;validation error;PIL22003;Error;DUPLICATE FILE. FILE ALREADY PROCESSED; Error Raised from IMP_CE_ASGN Collector
                """
            }
        },

        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "DEBUG",
                "formatter": "simple",
                "stream": "ext://sys.stdout"
            },

            "pil_engine": {
                "class": "logging.FileHandler",
                "level": "DEBUG",
                "formatter": "simple",
                "filename": "{log_dir}/pil_engine.{timestamp}.log",
                "encoding": "utf8"
            },

            # "log_handler (example)": {
            #    "class": "logging.handlers.RotatingFileHandler",
            #    "level": "INFO",
            #    "formatter": "simple",
            #    "filename": "{log_dir}/info.log",
            #    "maxBytes": 10485760,
            #    "backupCount": 20,
            #    "encoding": "utf8"
            # },
        },

        "root": {
            "level": "DEBUG",
            "handlers": ["console", "pil_engine"],
        }
    },
}
