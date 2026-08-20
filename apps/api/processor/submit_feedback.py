from langsmith import Client

ls_client= Client()


def submit_feedback(trace_id:str, feedback_score:int=None, feedback_text:str="", feedback_score_type:str="api"):
    if feedback_score is not None:
        ls_client.create_feedback(
            run_id=trace_id,
            key="thumbs",
            score=feedback_score,
            feedback_score_type=feedback_score_type
        )
    if len(feedback_text) > 0:
        ls_client.create_feedback(
            run_id=trace_id,
            key="comment",
            value=feedback_text,
            feedback_score_type=feedback_score_type
        )
        