# ----------------------------------------------------------------------------------------------------------------------
class DailyLimitForALadyIsExceededException(Exception):
    pass

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
class IntroLetterNotAllowedException(DirectSendLetterException):
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
    "msg_intro_not_allowed": IntroLetterNotAllowedException,
    "msg_max_intros_reached": LimitIsExceededException,

    "msg_second_intro_too_soon": SendingLetterTooSoonException,
    "msg_third_intro_too_soon": SendingLetterTooSoonException,
    "msg_fourth_intro_too_soon": SendingLetterTooSoonException,
    "msg_fifth_intro_too_soon": SendingLetterTooSoonException,
    "msg_sixth_intro_too_soon": SendingLetterTooSoonException,
    "msg_seventh_intro_too_soon": SendingLetterTooSoonException,
    "msg_eighth_intro_too_soon": SendingLetterTooSoonException,
    "msg_ninth_intro_too_soon": SendingLetterTooSoonException,
    "msg_tenth_intro_too_soon": SendingLetterTooSoonException,
}