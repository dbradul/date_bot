# ----------------------------------------------------------------------------------------------------------------------
class DirectSendLetterException(Exception):
    pass


# ----------------------------------------------------------------------------------------------------------------------
class AlreadySentIntroLetterException(DirectSendLetterException):
    pass


# ----------------------------------------------------------------------------------------------------------------------
class WomanBlockedByUserException(DirectSendLetterException):
    pass


# ----------------------------------------------------------------------------------------------------------------------
class SendingLetterTooSoonException(DirectSendLetterException):
    pass


# ----------------------------------------------------------------------------------------------------------------------
class IntoLetterNotAllowedException(DirectSendLetterException):
    pass


# ----------------------------------------------------------------------------------------------------------------------
class EmptyIntroLetterException(Exception):
    pass


# ----------------------------------------------------------------------------------------------------------------------
class LimitIsExceededException(Exception):
    pass


msg_id_exception_map = {
    "msg_intro_already_sent": AlreadySentIntroLetterException,
    "msg_woman_blocked_by_user": WomanBlockedByUserException,
    "msg_second_intro_too_soon": SendingLetterTooSoonException,
    "msg_third_intro_too_soon": SendingLetterTooSoonException,
    "msg_fourth_intro_too_soon": SendingLetterTooSoonException,
    "msg_fifth_intro_too_soon": SendingLetterTooSoonException,
    "msg_intro_not_allowed": IntoLetterNotAllowedException,
    "msg_max_intros_reached": LimitIsExceededException,
}