from reqPayloads.ReqPayload import ReqPayload

class CandidateFitAnalysisReqPayload(ReqPayload):
    def __init__(self, resume):
        super().__init__(resume, None)