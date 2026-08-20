from fastapi import  Request,APIRouter
from apps.api.processor.submit_feedback import submit_feedback
from apps.api.models.schema import FeedbackRequest, FeedbackResponse

feedback_router = APIRouter()


@feedback_router.post("/")
def send_feedback(request:Request, payload: FeedbackRequest)-> FeedbackResponse:


    submit_feedback(payload.trace_id, payload.feedback_score,payload.feedback_text, payload.feedback_score_type)
    return FeedbackResponse(
        status="success"
    )
