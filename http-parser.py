#!/usr/bin/python3

HTTP_LINE_DELIM = "\r\n"


class HttpHeader:
    def __init__(self):
        self.headers = {}
        self.method = ""
        self.path = ""
        self.protocol = ""
        self.errCode = 0
        self.isResponse = False

    def __str__(self):
        if self.isResponse:
            return "%s %s %s %s\n" % (
                self.protocol,
                self.errCode,
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

    def errCodeDescription(self):
        return {
            404: ""
        }[self.errCode]


def parseReqHeader(headerStr):
    errors = []
    result = HttpHeader()

    lines = headerStr.split(HTTP_LINE_DELIM)
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
                errors.append("The first line only had %d items!" % len(fields))
    if len(errors) > 0:
        return None, errors

    return result, None


def makeResHeader():
    hdr = HttpHeader()
    hdr.isResponse = True
    hdr.errCode = 200
    return hdr

if __name__ == "__main__":
    testHeaderLines = [
        "GET http://choices.truste.com/get?name=admarker-icon-tl.png HTTP/1.1",
        "User-Agent: Mozilla/5.0",
        ""
    ]
    testHeaderStr = HTTP_LINE_DELIM.join(testHeaderLines)
    (testHeader, errs) = parseReqHeader(testHeaderStr)
    print(testHeader, errs)

