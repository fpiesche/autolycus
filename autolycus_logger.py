import logging

class AutolycusFormatter(logging.Formatter):

    err_fmt  = '❌  %(msg)s'
    dbg_fmt  = '🐞  %(module)s: %(lineno)d: %(msg)s'
    info_fmt = 'ℹ️  %(msg)s'
    warning_fmt = '⚠️  %(msg)s'
    critical_fmt = '🚨  %(msg)s'

    def __init__(self):
        super().__init__(fmt='%(levelno)d: %(msg)s', datefmt=None, style='%')  

    def format(self, record):

        # Save the original format configured by the user
        # when the logger formatter was instantiated
        format_orig = self._style._fmt

        # Replace the original format with one customized by logging level
        if record.levelno == logging.DEBUG:
            self._style._fmt = AutolycusFormatter.dbg_fmt

        elif record.levelno == logging.INFO:
            self._style._fmt = AutolycusFormatter.info_fmt

        elif record.levelno == logging.ERROR:
            self._style._fmt = AutolycusFormatter.err_fmt

        elif record.levelno == logging.WARNING:
            self._style._fmt = AutolycusFormatter.warning_fmt

        elif record.levelno == logging.CRITICAL:
            self._style._fmt = AutolycusFormatter.critical_fmt

        # Call the original formatter class to do the grunt work
        result = logging.Formatter.format(self, record)

        # Restore the original format configured by the user
        self._style._fmt = format_orig

        return result