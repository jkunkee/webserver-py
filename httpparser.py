#!/usr/bin/python3

# time formatting
from time import mktime
from datetime import datetime
from email.utils import formatdate


HTTP_LINE_DELIM = b"\r\n"
HTTP_MSG_END = HTTP_LINE_DELIM + HTTP_LINE_DELIM

HTTP_LINE_DELIM_STR = HTTP_LINE_DELIM.decode("utf-8")


class HttpHeader:

    def __init__(self):
        self.headers = {}
        self.method = ""
        self.path = ""
        self.protocol = ""
        self.responseCode = 0
        self.isResponse = False

    def __str__(self):
        if self.isResponse:
            return "%s %s %s %s\n" % (
                self.protocol,
                self.responseCode,
                self.errCodeDescription(),
                self.headers,
            )
        else:
            return "%s %s %s %s\n" % (
                self.method,
                self.path,
                self.protocol,
                self.headers,
            )

    def toHttp(self):
        lines = []

        # get the first line built up
        firstLine = ""
        if self.isResponse:
            firstLine = ("%s %s %s") % (
                self.protocol, self.responseCode, self.errCodeDescription()
            )
        else:
            firstLine = ("%s %s %s") % (
                self.method, self.path, self.protocol
            )
        lines.append(firstLine)

        # assemble the headers
        for headerName in self.headers.keys():
            lines.append("%s: %s" % (
                headerName, self.headers[headerName],
            ))

        # ensure the end is correct
        lines.append(HTTP_LINE_DELIM_STR)
        # assemble the troops
        return HTTP_LINE_DELIM_STR.join(lines)

    def errCodeDescription(self):
        return {
            200: "OK",
            400: "Bad Request",
            403: "Forbidden",
            404: "Not Found",
            418: "I am a teapot",
            500: "Internal Server Erro",
            501: "Not Implemented",
        }[self.responseCode]


def parseReqHeader(headerBytes):
    errors = []
    result = HttpHeader()

    headerStr = headerBytes.decode("utf-8")

    lines = headerStr.split(HTTP_LINE_DELIM_STR)
    if len(lines) < 2:
        errors.append("Didn't find enough lines to parse as HTTP Headers")
        return None, errors
    for idx, line in enumerate(lines):
        if idx == 0:
            fields = line.split()
            if len(fields) == 3:
                result.method = fields[0]
                result.path = fields[1]
                result.protocol = fields[2]
            else:
                errors.append(
                    "The first line only had %d items!" % len(fields)
                )
        else:
            pair = line.split(":", 1)
            if line == "":
                continue

            if len(pair) == 2:
                headerName = pair[0]
                headerVal = pair[1]
                if headerVal[0] == " ":
                    headerVal = headerVal[1:]
                result.headers[headerName] = headerVal
            else:
                print("Invalid header!", pair, line)
    if len(errors) > 0:
        return None, errors

    return result, None


def makeResHeader(responseCode=200):
    hdr = HttpHeader()
    hdr.protocol = "HTTP/1.1"
    hdr.isResponse = True
    hdr.responseCode = responseCode
    # default headers
    hdr.headers["Server"] = "Jon's pyHttp v0.1.0"
    hdr.headers["Date"] = mkHttpTimestamp()
    hdr.headers["Content-Length"] = 0
    return hdr

if __name__ == "__main__":
    testHeaderLines = [
        b"GET /get?name=admarker-icon-tl.png HTTP/1.1",
        b"User-Agent: Mozilla/5.0",
        b"Host: www.something.com",
        b""
    ]
    testHeaderStr = HTTP_LINE_DELIM.join(testHeaderLines)
    (testHeader, errs) = parseReqHeader(testHeaderStr)
    print(testHeader, errs)
    print(testHeader.toHttp())


# mkHttpTimestamp imports and code pulled from
# http://stackoverflow.com/a/225106
def mkHttpTimestamp():
    now = datetime.now()
    stamp = mktime(now.timetuple())
    return formatdate(
        timeval=stamp,
        localtime=False,
        usegmt=True,
    )
