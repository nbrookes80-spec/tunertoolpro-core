"""GMLAN message definitions for General Motors high-speed (11-bit, 500 kbit/s) CAN traffic.

The message names and signal lists come from the gmlan-main project's README (E38 PCM and T43 TCM vehicle,
GMW8762 family). The project gives signal names but not bit positions or scaling for most signals, so this
module labels frames and checks them against the documented example payloads. It does not turn bytes
into engine speed or gear values it cannot justify. Read-only: nothing here transmits.

Source of the table: gmlan-main/README.md. Regenerate it by hand from there if the README changes.
"""

from dataclasses import dataclass
from typing import Optional, Tuple

from .frames import Frame


@dataclass(frozen=True)
class GmlanExample:
    payload: str            # hex data bytes, no spaces, e.g. '0F0F000100000300'
    meaning: Optional[str]  # what the README says it means, when it says


@dataclass(frozen=True)
class GmlanMessage:
    can_id: int
    sender: Optional[str]           # 'GW tx', 'TCM,ECM tx', or None when the README does not say
    signals: Tuple[str, ...]        # signal names, in the README's order
    examples: Tuple[Tuple[str, Optional[str]], ...]

    @property
    def name(self):
        return f'GMLAN 0x{self.can_id:03X}'

    def example_for(self, data):
        """The documented example whose payload equals data, or None."""
        text = bytes(data).hex().upper()
        for payload, meaning in self.examples:
            if payload == text:
                return GmlanExample(payload, meaning)
        return None


MESSAGES = {
    0x0C9: GmlanMessage(
        0x0C9,
        None,
        ('Accelerator actual position', 'Accelerator actual position validity', 'Engine run active', 'Engine speed', 'Engine speed status', 'Platform engines speed command inhibit request', 'Power takeoff powertrain Run aborted', 'Powertrain brake pedal discrete input', 'Powertrain brake pedal discrete input validity', 'Powertrain crank aborted', 'Powertrain crank active', 'Powertrain run aborted', 'Remote vehicle start engine running', 'Cylinder deactivation mode', 'Engine Idle active', 'Driver throttle override detected', 'Cruise control enabled', 'Cruise control active status'),
        (),
    ),
    0x0F9: GmlanMessage(
        0x0F9,
        None,
        ('Transmission Output shaft angular velocity', 'Transmission Output shaft angular velocity sensor present', 'Transmission Output shaft angular velocity validity', 'Transmission overall estimated torque ratio', 'Transmission overall estimated torque ratio validity'),
        (),
    ),
    0x1F3: GmlanMessage(
        0x1F3,
        'GW tx',
        ('Overdrive disable requested', 'Platform transmission tap up/tap down enable switch state', 'Platform transmission tap up/tap down switch state', 'Platform transmission tap up/tap down switch status rolling count', 'Transmission oil life reset request', 'Transmission platform shift pattern switch 1 active', 'Transmission platform shift pattern switch 2 active', 'Transmission platform shift pattern switch 3 active', 'Transmission platform shift pattern switch 4 active', 'Transmission platform shift pattern switch alive rolling count'),
        (),
    ),
    0x1F5: GmlanMessage(
        0x1F5,
        'TCM,ECM tx',
        ('Automatic transmission commanded gear', 'Automatic transmission gear shift direction', 'Driver shift control request denied indicator on', 'Driver shift control target gear', 'Engine recommended upshift indicator on', 'Overdrive Disable Granted', 'Top of travel clutch switch active', 'Top of travel clutch switch active validity', 'Transmission creep mode active', 'Transmission estimated gear', 'Transmission estimated gear validity', 'Transmission range inhibit status', 'Transmission shift lever lock requested', 'Transmission shift lever position', 'Transmission shift lever position validity', 'Transmission shift mode status', 'Transmission shift pattern active status', 'Transmission skip shift indicator on', 'Transmission Tap up/Tap down mode status'),
        (('0F0F000100000300', 'Park'), ('0F0F000200000300', 'Reverse'), ('0F0F000300000300', 'Neutral'), ('0F0F000400000300', 'Drive')),
    ),
    0x4E9: GmlanMessage(
        0x4E9,
        'GW tx',
        ('Ac compressor type', 'Elapsed time count', 'Elapsed time count reset occurred', 'Antilock braking system present', 'Platform engine speed commend system type', 'Traction control system present', 'Vehicle speed control system type', 'Vehicle stability enhancement system present'),
        (('01003C11C6', None), ('01003C13A2', None)),
    ),
    0x1E1: GmlanMessage(
        0x1E1,
        'GW tx',
        ('Cruise Control Cancel Request', 'Cruise control switch status', 'Cruise control switch status alive rolling count', 'Cruise control switch status protection value'),
        (('0000040000', None), ('00FF050020', None), ('00FE060040', None), ('00FD070060', None)),
    ),
    0x1F1: GmlanMessage(
        0x1F1,
        'GW tx',
        ('Display measurement system', 'Engine oil life reset request', 'Immobilizer pre release password', 'Immobilizer pre release password status', 'Park brake switch active', 'Park brake virtual device availablity', 'Power mode master accessory', 'Power mode master run crank terminal status', 'Power takeoff remote start master engine shutdown request', 'Power takeoff remote start master engine start request', 'Remote vehicle start request', 'System backup power mode', 'System backup power mode enabled', 'System power mode', 'Throttle progression request'),
        (('0500000008000070', None),),
    ),
}


# The modules the README's definitions were captured from.
SUPPORTED_ECM = 'E38'   # Powertrain Control Module
SUPPORTED_TCM = 'T43'   # Transmission Control Module


def _module_code(label):
    """'E38', 'e38 (confirm)' -> 'E38'. Blank or None -> ''."""
    text = (label or '').strip().upper()
    return text.split()[0] if text else ''


def supports(ecm_label, tcm_label):
    """True when a car's ECM and TCM labels are the ones this table was written for."""
    return _module_code(ecm_label) == SUPPORTED_ECM and _module_code(tcm_label) == SUPPORTED_TCM


def lookup(can_id):
    """The GMLAN definition for an 11-bit ID, or None if the README does not describe it."""
    return MESSAGES.get(can_id)


def describe(frame: Frame):
    """(message, example) for a frame. Either part is None when there is nothing to report."""
    message = lookup(frame.can_id)
    if message is None or frame.extended:
        return None, None
    return message, message.example_for(frame.data)
