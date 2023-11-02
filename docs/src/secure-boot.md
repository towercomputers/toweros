# Secure Boot

*Secure Boot* is a security feature that is implemented in the BIOS and does not require special hardware. Secure Boot ensures that each component launched during the boot process is digitally signed, and that the signature is validated against a set of trusted certificates embedded in the UEFI BIOS.

TowerOS offers the possibility to activate Secure Boot on the thin client. To do this, the firmware must be correctly configured before and after installation.

## Before the installation

You must:

- Disable Secure Boot if necessary
- Reset to "Setup Mode"
- Clear all secure boot keys that have already been registered

On ThinkPad firmware, these three things can be done on the same screen:

![alt text](./img/ThinkPadSecureBoot.jpg)

## After the installation

You must enable the "Secure Boot" feature on the same screen.

*Attention*---once activated, you will not be able to boot from unsigned devices, for example a live system on an USB key. It will first be necessary to deactivate the Secure Boot feature.

Remember to make a backup of the private keys used for Secure Boot, which are located here by default in `/usr/share/secureboot/keys/`.
