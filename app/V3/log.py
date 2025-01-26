import logging

def log(logger_name, logger_file_name, conosole_format_string, file_format_string):
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    file_handler = logging.FileHandler(logger_file_name)

    console_handler.setLevel(logging.DEBUG)
    file_handler.setLevel(logging.INFO)

    console_format = logging.Formatter(conosole_format_string)
    file_format = logging.Formatter(file_format_string)
    console_handler.setFormatter(console_format)
    file_handler.setFormatter(file_format)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger 

